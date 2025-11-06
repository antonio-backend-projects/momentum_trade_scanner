import math
import os
from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd

from utils.indicators import atr, rolling_median_vol, vwap
from utils.levels import floor_pivots, opening_range
from utils.confluence import ConfluenceScorer

DEBUG = os.environ.get("STRAT_DEBUG", "0") == "1"
def dlog(*args):
    if DEBUG: print("[DBG]", *args)

LOCAL_TZ = "America/New_York"

@dataclass
class Cfg:
    proximity_atr: float
    time_window_min: int
    volume_mult_break: float
    stop_atr: float
    tp_atr: float
    notional: float
    max_positions: int
    daily_max_loss_R: float

class PivotConfluenceStrategy:
    def __init__(self, cfg: Dict[str, Any]):
        r = cfg['rules']; risk = cfg['risk']
        self.cfg = cfg
        self.params = Cfg(
            proximity_atr = float(r.get('proximity_atr_1m', 0.2)),
            time_window_min = int(r.get('time_window_min', 0)),
            volume_mult_break = float(r.get('volume_mult_break', 1.5)),
            stop_atr = float(risk.get('stop_atr', 0.3)),
            tp_atr = float(risk.get('take_profit_atr', 0.6)),
            notional = float(cfg['orders'].get('notional_per_trade', 5000)),
            max_positions = int(risk.get('max_positions', 2)),
            daily_max_loss_R = float(risk.get('daily_max_loss_R', 3.0)),
        )
        self.confluence = ConfluenceScorer(cfg)
        self.dm: Dict[str, pd.DataFrame] = {}

    def on_backtest_init(self, data_map: Dict[str, pd.DataFrame]):
        self.dm = {}
        for sym, df in data_map.items():
            if df is None or df.empty:
                self.dm[sym] = df
                continue
            d = df.copy()
            d["date_local"] = d.index.tz_convert(LOCAL_TZ).date
            d["atr1m"] = atr(d, 14).bfill()
            d["vol_med"] = rolling_median_vol(d, 20).bfill()
            d["vwap"] = (
                d.assign(_date=d["date_local"])
                 .groupby("_date", group_keys=False)[["high","low","close","volume"]]
                 .apply(vwap)
            )
            daily_high = d.groupby("date_local")["high"].transform("max")
            daily_low  = d.groupby("date_local")["low"].transform("min")
            d["pdh"] = daily_high.groupby(d["date_local"]).shift(1)
            d["pdl"] = daily_low.groupby(d["date_local"]).shift(1)
            last_close_prev = (
                d.groupby("date_local")["close"].transform("last")
                 .groupby(d["date_local"]).shift(1)
            )
            d["pdc"] = last_close_prev
            self.dm[sym] = d

    def _near_any_level(self, row: pd.Series, day_df: pd.DataFrame):
        near = False; target = None; name = None
        atrv = row.get('atr1m', None)
        if atrv is None or (isinstance(atrv, float) and math.isnan(atrv)) or atrv <= 0:
            return False, None, None

        prev_day = day_df.iloc[:-1] if len(day_df) > 1 else day_df
        piv = floor_pivots(prev_day)
        candidates = {'PP':piv['PP'], 'R1':piv['R1'], 'S1':piv['S1']}
        if len(day_df) >= max(1, self.cfg["levels"].get("opening_range_min", 5)):
            orh, orl = opening_range(day_df, minutes=self.cfg["levels"].get("opening_range_min", 5))
            candidates['ORH'] = orh; candidates['ORL'] = orl
        vwap_val = row.get('vwap', None)
        if pd.notna(vwap_val): candidates['VWAP'] = vwap_val
        if pd.notna(row.get('pdh')): candidates['PDH'] = row['pdh']
        if pd.notna(row.get('pdl')): candidates['PDL'] = row['pdl']
        if pd.notna(row.get('pdc')): candidates['PDC'] = row['pdc']

        for nm, lv in candidates.items():
            if lv is None or (isinstance(lv, float) and pd.isna(lv)):
                continue
            if abs(row['close'] - lv) <= self.params.proximity_atr * atrv:
                near, target, name = True, lv, nm
                break
        return near, target, name

    def _break_trigger(self, row: pd.Series, target: float):
        vol_ok = row['volume'] >= self.params.volume_mult_break * row['vol_med']
        is_long = row['close'] > target and row['open'] <= target
        is_short = row['close'] < target and row['open'] >= target
        return vol_ok, is_long, is_short

    def _size_qty(self, price: float):
        return max(1, int(self.params.notional / price)) if price > 0 else 0

    def _exit_prices(self, entry: float, atrv: float, side: str):
        sl = entry - self.params.stop_atr * atrv if side == "buy" else entry + self.params.stop_atr * atrv
        tp = entry + self.params.tp_atr * atrv if side == "buy" else entry - self.params.tp_atr * atrv
        return sl, tp

    def on_bar_backtest(self, ts, bar_map):
        fills = []
        near_map = {}

        all_syms = self.cfg['universe']['main'] + sorted({x for lst in self.cfg['universe'].get('confirms',{}).values() for x in lst})
        for sym in all_syms:
            d = self.dm.get(sym)
            if d is None or d.empty or ts not in d.index:
                continue
            row = d.loc[ts]
            day_df = d[d['date_local'] == ts.tz_convert(LOCAL_TZ).date()]
            near, _, _ = self._near_any_level(row, day_df)
            near_map[sym] = near

        for sym in self.cfg['universe']['main']:
            d = self.dm.get(sym)
            if d is None or d.empty or ts not in d.index:
                continue
            row = d.loc[ts]
            day_df = d[d['date_local'] == ts.tz_convert(LOCAL_TZ).date()]

            near, target, lname = self._near_any_level(row, day_df)
            if not near:
                dlog(ts, sym, "skip:not_near_level")
                continue

            conf = self.confluence.score(sym, near_map)
            if conf < int(self.cfg['rules'].get('min_confluence', 1)):
                dlog(ts, sym, f"skip:low_confluence conf={conf}")
                continue

            vol_ok, is_long, is_short = self._break_trigger(row, target)
            if not vol_ok:
                dlog(ts, sym, f"skip:low_volume vol={row['volume']} med={row['vol_med']}")
                continue
            if not (is_long or is_short):
                dlog(ts, sym, f"skip:no_break close={row['close']} tgt={target}")
                continue

            atrv = row['atr1m']; px = row['close']
            qty = self._size_qty(px)
            if qty <= 0:
                dlog(ts, sym, f"skip:qty0 px={px}")
                continue

            side = "buy" if is_long else "sell"
            sl, tp = self._exit_prices(px, atrv, side)

            pnl = (tp - px)*qty if side=="buy" else (px - tp)*qty
            R = (self.params.tp_atr / self.params.stop_atr) if self.params.stop_atr > 0 else 0.0
            fills.append([ts, sym, side, px, tp, qty, pnl, R])
        return fills

    def on_poll(self, api, symbols):
        print("Poll tick - demo mode. Esporta CSV e usa backtest per ora.")
