import math
import pandas as pd
from typing import Dict, Any
from dataclasses import dataclass
from .strategy_utils import Trade, Position
from utils.indicators import atr, rolling_median_vol, vwap
from utils.levels import floor_pivots, opening_range
from utils.confluence import ConfluenceScorer

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
        self.opening_range_min = int(r.get('opening_range_min', 5))
        self.min_confluence = int(r.get('min_confluence', 1))
        self.break_buffer_atr = float(r.get('break_buffer_atr', 0.0))
        self.range_min_atr = float(r.get('range_min_atr', 0.0))
        self.level_cooldown_min = int(r.get('level_cooldown_min', 0))
        self._level_last_ts = {}
        self.confluence = ConfluenceScorer(cfg)
        self.dm: Dict[str, pd.DataFrame] = {}

    def on_backtest_init(self, data_map: Dict[str, pd.DataFrame]):
        for sym, df in data_map.items():
            d = df.copy()
            d['atr1m'] = atr(d, 14).bfill()
            d['vol_med'] = rolling_median_vol(d, 20).bfill()
            d['date'] = d.index.date
            d['vwap'] = d.groupby('date', group_keys=False)[['high','low','close','volume']].apply(vwap)
            d['pdh'] = d.groupby('date')['high'].transform('max').shift(1)
            d['pdl'] = d.groupby('date')['low'].transform('min').shift(1)
            d['pdc'] = d['close'].shift(1).where(d['date'] != pd.Series(d['date']).shift(1).values, None)
            d['ema20'] = d['close'].ewm(span=20, adjust=False).mean()
            d['ema50'] = d['close'].ewm(span=50, adjust=False).mean()
            self.dm[sym] = d

    def _near_any_level(self, row: pd.Series, day_df: pd.DataFrame):
        near = False; target = None; name = None
        atrv = row.get('atr1m', None)
        if atrv is None or (isinstance(atrv, float) and math.isnan(atrv)) or atrv <= 0:
            return False, None, None

        prev_day = day_df.iloc[:-1] if len(day_df) > 1 else day_df
        piv = floor_pivots(prev_day)
        candidates = {'PP':piv['PP'], 'R1':piv['R1'], 'S1':piv['S1']}
        if len(day_df) >= self.opening_range_min:
            orh, orl = opening_range(day_df, minutes=self.opening_range_min)
            candidates['ORH'] = orh; candidates['ORL'] = orl
        vwap_val = row.get('vwap', None)
        if pd.notna(vwap_val): candidates['VWAP'] = vwap_val
        if pd.notna(row.get('pdh')): candidates['PDH'] = row['pdh']
        if pd.notna(row.get('pdl')): candidates['PDL'] = row['pdl']
        if pd.notna(row.get('pdc')): candidates['PDC'] = row['pdc']

        for nm, lv in candidates.items():
            if lv is None or (isinstance(lv, float) and math.isnan(lv)):
                continue
            if abs(row['close'] - lv) <= self.params.proximity_atr * atrv:
                near, target, name = True, lv, nm
                break
        return near, target, name

    def _break_trigger(self, row: pd.Series, target: float, atrv: float):
        vol_ok = row['volume'] >= self.params.volume_mult_break * row['vol_med']
        buf = self.break_buffer_atr * atrv
        rng_ok = (row['high'] - row['low']) >= self.range_min_atr * atrv

        is_long = (row['close'] > target + buf) and (row['open'] <= target)
        is_short = (row['close'] < target - buf) and (row['open'] >= target)
        return (vol_ok and rng_ok), is_long, is_short

    def _trend_ok(self, row: pd.Series, side: str):
        above_vwap = (pd.notna(row.get('vwap')) and row['close'] >= row['vwap'])
        ema_ok_long = (pd.notna(row.get('ema20')) and pd.notna(row.get('ema50')) and row['ema20'] >= row['ema50'])
        ema_ok_short = (pd.notna(row.get('ema20')) and pd.notna(row.get('ema50')) and row['ema20'] <= row['ema50'])
        if side == "buy":
            return (not pd.isna(row.get('vwap'))) and above_vwap and ema_ok_long
        else:
            return (not pd.isna(row.get('vwap'))) and (not above_vwap) and ema_ok_short

    def _size_qty(self, price: float):
        return max(1, int(self.params.notional / price)) if price > 0 else 0

    def _exit_prices(self, entry: float, atrv: float, side: str):
        sl = entry - self.params.stop_atr * atrv if side == "buy" else entry + self.params.stop_atr * atrv
        tp = entry + self.params.tp_atr * atrv if side == "buy" else entry - self.params.tp_atr * atrv
        return sl, tp

    def _simulate_bracket(self, d: pd.DataFrame, ts, side: str, entry: float, atrv: float):
        sl, tp = self._exit_prices(entry, atrv, side)
        max_hold = int(self.cfg.get('backtest', {}).get('max_hold_min', 30))
        fee = float(self.cfg.get('backtest', {}).get('commission_per_share', 0.0))
        slip_bps = float(self.cfg.get('backtest', {}).get('slippage_bps', 0.0))

        day = ts.date()
        future = d[(d.index > ts) & (d['date'] == day)].iloc[:max_hold]
        if future.empty:
            exit_px = entry
        else:
            exit_px = entry
            who = None
            for _, bar in future.iterrows():
                lo, hi = float(bar['low']), float(bar['high'])
                if side == "buy":
                    if lo <= sl: exit_px = sl; break
                    if hi >= tp: exit_px = tp; break
                else:
                    if hi >= sl: exit_px = sl; break
                    if lo <= tp: exit_px = tp; break
            else:
                exit_px = future['close'].iloc[-1]

        entry_adj = entry * (1 + (slip_bps/1e4) * (1 if side=="buy" else -1))
        exit_adj  = exit_px * (1 - (slip_bps/1e4) * (1 if side=="buy" else -1))
        return exit_adj, sl, tp

    def on_bar_backtest(self, ts, bar_map):
        fills = []
        near_map = {}

        all_syms = self.cfg['universe']['main'] + sorted({x for lst in self.cfg['universe'].get('confirms',{}).values() for x in lst})
        all_syms = list(dict.fromkeys(all_syms))
        for sym in all_syms:
            d = self.dm.get(sym)
            if d is None or ts not in d.index:
                continue
            row = d.loc[ts]
            day_df = d[d['date'] == ts.date()]
            near, _, _ = self._near_any_level(row, day_df)
            near_map[sym] = near

        for sym in self.cfg['universe']['main']:
            d = self.dm.get(sym)
            if d is None or ts not in d.index:
                continue
            row = d.loc[ts]
            day_df = d[d['date'] == ts.date()]

            near, target, lname = self._near_any_level(row, day_df)
            if not near:
                continue
            conf = self.confluence.score(sym, near_map)
            if conf < self.min_confluence:
                continue

            atrv = float(row['atr1m'])
            vol_ok, is_long, is_short = self._break_trigger(row, target, atrv)
            if not vol_ok or (not is_long and not is_short):
                continue

            px = float(row['close'])
            side = "buy" if is_long else "sell"
            if not self._trend_ok(row, side):
                continue

            key = (sym, lname)
            last = getattr(self, "_level_last_ts", {}).get(key)
            if last is not None:
                if (ts - last).total_seconds() < self.level_cooldown_min * 60:
                    continue
            self._level_last_ts[key] = ts

            qty = max(1, int(self.params.notional / px))
            if qty <= 0: 
                continue

            exit_px, sl, tp = self._simulate_bracket(d, ts, side, px, atrv)
            fee = float(self.cfg.get('backtest', {}).get('commission_per_share', 0.0))
            costs = fee * qty * 2.0
            if side == "buy":
                pnl = (exit_px - px) * qty - costs
            else:
                pnl = (px - exit_px) * qty - costs

            r_per_share = abs(self.params.stop_atr * atrv)
            R = (pnl / (r_per_share * qty)) if r_per_share > 0 else 0.0

            fills.append([ts, sym, side, px, exit_px, qty, pnl, R])
        return fills

    def on_poll(self, api, symbols):
        print("Poll tick - demo mode. Esporta CSV e usa backtest per ora.")
