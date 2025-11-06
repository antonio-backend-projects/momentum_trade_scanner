import math
import pandas as pd
from typing import Dict, Any, List, Tuple
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
        self.risk_perc = float(risk.get('risk_per_trade_pct', 0.0))
        self.account_equity = float(risk.get('account_equity', 0.0))
        self.confluence = ConfluenceScorer(cfg)
        self.dm: Dict[str, pd.DataFrame] = {}

        # trend / candle filters params
        tf = r.get('trend_filters', {}) or {}
        self.use_ema = bool(tf.get('use_ema', False))
        self.ema_fast = int(tf.get('ema_fast', 20))
        self.ema_slow = int(tf.get('ema_slow', 50))
        self.use_vwap_filter = bool(tf.get('use_vwap', False))

        cf = r.get('candle_filters', {}) or {}
        self.min_body_atr = float(cf.get('min_body_atr', 0.0))

        self.min_conf = int(r.get('min_confluence', 0))
        self.buf_mult = float(r.get('break_buffer_atr', 0.0))

    def on_backtest_init(self, data_map: Dict[str, pd.DataFrame]):
        for sym, df in data_map.items():
            d = df.copy()

            # Indicatori base
            d['atr1m'] = atr(d, 14).ffill().bfill()
            d['vol_med'] = rolling_median_vol(d, 20).ffill().bfill()

            # Timezone-safe date col
            idx = d.index
            if getattr(idx, "tz", None) is not None:
                d['date'] = idx.tz_convert('UTC').date
            else:
                d['date'] = pd.to_datetime(idx).date

            # VWAP per giorno
            d['vwap'] = d.groupby('date', group_keys=False)[['high','low','close','volume']].apply(vwap)

            # EMA per trend filter (calcolate globalmente; non per giorno)
            d['ema_fast'] = d['close'].ewm(span=self.ema_fast, adjust=False).mean()
            d['ema_slow'] = d['close'].ewm(span=self.ema_slow, adjust=False).mean()

            # Livelli del giorno precedente
            d['pdh'] = d.groupby('date')['high'].transform('max').shift(1)
            d['pdl'] = d.groupby('date')['low'].transform('min').shift(1)
            d['pdc'] = d.groupby('date')['close'].transform('last').shift(1)

            self.dm[sym] = d

    def _near_any_level(self, row: pd.Series, day_df: pd.DataFrame) -> Tuple[bool, float, str]:
        atrv = row.get('atr1m', None)
        if atrv is None or pd.isna(atrv) or atrv <= 0:
            return False, None, None

        prev_day = day_df.iloc[:-1] if len(day_df) > 1 else day_df
        piv = floor_pivots(prev_day) if len(prev_day) > 0 else {'PP': None, 'R1': None, 'S1': None}
        candidates = {'PP': piv.get('PP'), 'R1': piv.get('R1'), 'S1': piv.get('S1')}

        or_min = int(self.cfg['levels'].get('opening_range_min', 5))
        if len(day_df) >= max(1, or_min):
            orh, orl = opening_range(day_df, minutes=or_min)
            candidates['ORH'] = orh; candidates['ORL'] = orl

        if pd.notna(row.get('vwap')): candidates['VWAP'] = float(row['vwap'])
        if pd.notna(row.get('pdh')):  candidates['PDH']  = float(row['pdh'])
        if pd.notna(row.get('pdl')):  candidates['PDL']  = float(row['pdl'])
        if pd.notna(row.get('pdc')):  candidates['PDC']  = float(row['pdc'])

        for nm, lv in candidates.items():
            if lv is None or pd.isna(lv):
                continue
            if abs(row['close'] - lv) <= self.params.proximity_atr * atrv:
                return True, float(lv), nm
        return False, None, None

    def _passes_trend_filters(self, row: pd.Series, side: str) -> bool:
        if self.use_ema:
            ef, es = row.get('ema_fast'), row.get('ema_slow')
            if pd.isna(ef) or pd.isna(es):
                return False
            if side == "buy" and not (row['close'] > ef > es):
                return False
            if side == "sell" and not (row['close'] < ef < es):
                return False
        if self.use_vwap_filter:
            v = row.get('vwap')
            if pd.isna(v):
                return False
            if side == "buy" and not (row['close'] >= v):
                return False
            if side == "sell" and not (row['close'] <= v):
                return False
        return True

    def _passes_candle_filter(self, row: pd.Series) -> bool:
        if self.min_body_atr <= 0:
            return True
        atrv = row.get('atr1m')
        if pd.isna(atrv) or atrv <= 0:
            return False
        body = abs(float(row['close']) - float(row['open']))
        return body >= self.min_body_atr * float(atrv)

    def _break_trigger(self, row: pd.Series, target: float):
        vol_ok = (
            pd.notna(row.get('volume')) and pd.notna(row.get('vol_med')) and
            row['volume'] >= self.params.volume_mult_break * row['vol_med']
        )
        is_long = pd.notna(target) and row['close'] > (target + self.buf_mult * row['atr1m']) and row['open'] <= target
        is_short = pd.notna(target) and row['close'] < (target - self.buf_mult * row['atr1m']) and row['open'] >= target
        return vol_ok, is_long, is_short

    def _size_qty(self, price: float, atrv: float) -> int:
        # priority: risk-based sizing
        if self.risk_perc > 0 and self.account_equity > 0 and atrv > 0:
            stop_dist = self.params.stop_atr * atrv
            risk_usd = self.account_equity * self.risk_perc
            if stop_dist <= 0:
                return 0
            qty = int(max(1, math.floor(risk_usd / stop_dist)))
            return qty
        # fallback: notional
        if price is None or not isinstance(price, (int, float)) or price <= 0:
            return 0
        return max(1, int(self.params.notional / price))

    def _exit_prices(self, entry: float, atrv: float, side: str):
        if any(pd.isna(x) for x in [entry, atrv]) or atrv <= 0:
            return None, None
        sl = entry - self.params.stop_atr * atrv if side == "buy" else entry + self.params.stop_atr * atrv
        tp = entry + self.params.tp_atr * atrv if side == "buy" else entry - self.params.tp_atr * atrv
        return float(sl), float(tp)

    def on_bar_backtest(self, ts, bar_map) -> List[list]:
        signals: List[list] = []
        near_map: Dict[str, bool] = {}

        # confluence map
        all_syms = self.cfg['universe']['main'] + sorted({
            x for lst in self.cfg['universe'].get('confirms', {}).values() for x in lst
        })
        for sym in all_syms:
            d = self.dm.get(sym)
            if d is None or ts not in d.index:
                continue
            row = d.loc[ts]
            day_df = d[d['date'] == ts.date()]
            near, _, _ = self._near_any_level(row, day_df)
            near_map[sym] = bool(near)

        # signals
        for sym in self.cfg['universe']['main']:
            d = self.dm.get(sym)
            if d is None or ts not in d.index:
                continue
            row = d.loc[ts]
            day_df = d[d['date'] == ts.date()]

            near, target, _lname = self._near_any_level(row, day_df)
            if not near or target is None:
                continue

            conf = self.confluence.score(sym, near_map)
            if conf < self.min_conf:
                continue

            if not self._passes_candle_filter(row):
                continue

            vol_ok, is_long, is_short = self._break_trigger(row, target)
            if not vol_ok or (not is_long and not is_short):
                continue

            side = "buy" if is_long else "sell"
            if not self._passes_trend_filters(row, side):
                continue

            atrv = float(row['atr1m'])
            entry = (target + self.buf_mult * atrv) if side == "buy" else (target - self.buf_mult * atrv)
            qty = self._size_qty(entry, atrv)
            if qty <= 0:
                continue

            sl, tp = self._exit_prices(entry, atrv, side)
            if sl is None or tp is None:
                continue

            signals.append([ts, sym, side, float(entry), int(qty), float(sl), float(tp)])

        return signals

    def on_poll(self, api, symbols):
        print("Poll tick - demo mode. Esporta CSV e usa backtest per ora.")
