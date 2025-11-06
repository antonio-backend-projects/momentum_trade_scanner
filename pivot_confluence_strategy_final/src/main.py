import argparse, os, yaml
from dotenv import load_dotenv
from backtest.backtest import Backtester
from execution.alpaca_broker import AlpacaBroker
from strategies.pivot_confluence import PivotConfluenceStrategy

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["backtest","paper","live"])
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.mode in ("paper","live"):
        load_dotenv()
        broker = AlpacaBroker(env=os.environ, paper=(args.mode=="paper"))
        strat = PivotConfluenceStrategy(cfg)
        broker.run_streaming(strategy=strat, cfg=cfg)
    else:
        if args.start: cfg["backtest"]["start_date"] = args.start
        if args.end: cfg["backtest"]["end_date"] = args.end
        bt = Backtester(cfg, start_date=cfg["backtest"]["start_date"], end_date=cfg["backtest"]["end_date"])
        results = bt.run(PivotConfluenceStrategy(cfg))
        if results.empty:
            print("Nessun trade nel periodo selezionato.")
        else:
            # Export CSV
            out_csv = "backtest_trades.csv"
            results.to_csv(out_csv, index=False)
            print("\n=== BACKTEST SUMMARY ===")
            print(results.to_string(index=False))

            # Metriche
            import numpy as np
            pnl = results["pnl"].values
            R = results["R"].values
            n = len(results)
            wins = (pnl > 0).sum()
            winrate = wins / n if n > 0 else 0.0
            avg_R = float(np.mean(R)) if n > 0 else 0.0
            expectancy = float(np.mean(pnl)) if n > 0 else 0.0

            # equity e max drawdown
            eq = np.cumsum(pnl)
            peaks = np.maximum.accumulate(eq)
            dd = eq - peaks
            max_dd = float(dd.min()) if dd.size else 0.0

            print("\n=== METRICHE ===")
            print(f"Trades: {n}")
            print(f"Win rate: {winrate:.2%}")
            print(f"Expectancy (media PnL trade): {expectancy:.4f}")
            print(f"Media R: {avg_R:.2f}")
            print(f"Max Drawdown: {max_dd:.4f}")

            print("\nBy day:")
            print(bt.daily_pnl().to_string())

            print(f"\nTrade esportati in: {out_csv}")

if __name__ == "__main__":
    main()
