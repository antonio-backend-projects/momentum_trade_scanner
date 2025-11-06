import pandas as pd

class Backtester:
    def __init__(self, cfg):
        self.cfg = cfg
        self.start = pd.Timestamp(cfg['backtest']['start_date']).tz_localize('UTC')
        self.end   = pd.Timestamp(cfg['backtest']['end_date']).tz_localize('UTC')
        self.commission = float(cfg['backtest'].get('commission_per_share', 0.0))
        self.slip_bps   = float(cfg['backtest'].get('slippage_bps', 0.0))
        self.max_hold   = int(cfg['backtest'].get('max_hold_min', 30))

    def _load_csv_folder(self, folder, symbols):
        out = {}
        for s in symbols:
            df = pd.read_csv(f"{folder}/{s}.csv")
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df = df.set_index('timestamp').sort_index()
            df = df.loc[self.start:self.end].copy()
            for c in ['open','high','low','close','volume']:
                if c not in df.columns:
                    raise ValueError(f"CSV {s} missing column {c}")
            out[s] = df
        return out

    def _apply_costs(self, price, side, qty):
        slip = price * (self.slip_bps / 10000.0)
        px_filled = price + (slip if side == 'buy' else -slip)
        fees = self.commission * qty
        return px_filled, fees
    # qui
    # src/backtest/backtest.py

    def _simulate_entry(self, sym_df, ts_signal, side, entry_stop):
        """
        Trova la prima barra successiva a ts_signal e ritorna
        ESATTAMENTE ciò che il chiamante si aspetta: (ts_entry, px_entry_raw).
        """
        # prima barra STRICTLY AFTER il segnale
        start_idx = sym_df.index.searchsorted(ts_signal, side='right')
        if start_idx >= len(sym_df):
            return None

        ts_entry = sym_df.index[start_idx]
        px_entry_raw = float(sym_df.iloc[start_idx]['close'])
        return ts_entry, px_entry_raw

    def _simulate_exit_bracket(self, sym_df, i_entry, side, sl, tp):
        last_i = min(i_entry + self.max_hold, len(sym_df) - 1)
        for i in range(i_entry + 1, last_i + 1):
            lo, hi = sym_df.iloc[i][['low','high']]
            if side == 'buy':
                hit_sl = lo <= sl
                hit_tp = hi >= tp
                if hit_sl and hit_tp: return sym_df.index[i], float(sl), 'sl'
                if hit_sl: return sym_df.index[i], float(sl), 'sl'
                if hit_tp: return sym_df.index[i], float(tp), 'tp'
            else:
                hit_sl = hi >= sl
                hit_tp = lo <= tp
                if hit_sl and hit_tp: return sym_df.index[i], float(sl), 'sl'
                if hit_sl: return sym_df.index[i], float(sl), 'sl'
                if hit_tp: return sym_df.index[i], float(tp), 'tp'
        ts_exit = sym_df.index[last_i]
        px_exit = float(sym_df.iloc[last_i]['close'])
        return ts_exit, px_exit, 'timeout'

    def run(self, strategy):
        symbols = self.cfg['universe']['main'] + sorted(set(
            x for v in self.cfg['universe'].get('confirms', {}).values() for x in v
        ))
        data_map = self._load_csv_folder(self.cfg['data']['folder'], symbols)
        strategy.on_backtest_init(data_map)

        records = []
        timeline = sorted(set().union(*[data_map[s].index for s in self.cfg['universe']['main']]))

        for ts in timeline:
            signals = strategy.on_bar_backtest(ts, data_map)
            for (ts_sig, sym, side, entry_stop, qty, sl, tp) in signals:
                sym_df = data_map[sym]
                ent = self._simulate_entry(sym_df, ts_sig, side, entry_stop)
                if ent is None:
                    continue
                ts_entry, px_entry_raw = ent
                px_entry, fees_in = self._apply_costs(px_entry_raw, side, qty)

                i_entry = sym_df.index.get_loc(ts_entry)
                ts_exit, px_exit_raw, hit = self._simulate_exit_bracket(sym_df, i_entry, side, sl, tp)
                exit_side = 'sell' if side == 'buy' else 'buy'
                px_exit, fees_out = self._apply_costs(px_exit_raw, exit_side, qty)

                pnl = (px_exit - px_entry) * qty if side == 'buy' else (px_entry - px_exit) * qty
                pnl -= (fees_in + fees_out)
                risk_per_share = abs(px_entry - sl)
                R = (pnl / (risk_per_share * qty)) if risk_per_share > 0 else 0.0

                records.append([ts_entry, sym, side, round(px_entry,5), round(px_exit,5), int(qty), round(pnl,5), round(R,3), hit])

        cols = ['ts','symbol','side','px_entry','px_exit','qty','pnl','R','exit_reason']
        df = pd.DataFrame(records, columns=cols).sort_values('ts')
        if len(df) == 0:
            print("\n=== BACKTEST SUMMARY ===")
            print("No trades.\n")
            print("=== METRICHE ===\nTrades: 0")
            return []

        print("\n=== BACKTEST SUMMARY ===")
        print(df[['ts','symbol','side','px_entry','px_exit','qty','pnl','R','exit_reason']].to_string(index=False))

        wins = (df['pnl'] > 0).sum()
        tot  = len(df)
        wr   = 100.0 * wins / tot if tot else 0.0
        exp  = df['pnl'].mean() if tot else 0.0
        mR   = df['R'].mean() if tot else 0.0
        eq   = df['pnl'].cumsum()
        mdd  = float((eq.cummax() - eq).max()) if len(eq) else 0.0

        print("\n=== METRICHE ===")
        print(f"Trades: {tot}")
        print(f"Win rate: {wr:.2f}%")
        print(f"Expectancy (media PnL trade): {exp:.4f}")
        print(f"Media R: {mR:.2f}")
        print(f"Max Drawdown: {mdd:.4f}\n")

        by_day = df.groupby(df['ts'].dt.date)['pnl'].sum().to_frame('pnl')
        print("By day:")
        print(by_day.to_string())

        df.to_csv('backtest_trades.csv', index=False)
        print("\nTrade esportati in: backtest_trades.csv")
        return df
