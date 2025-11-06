import argparse, yaml, pandas as pd
from backtest.backtest import Backtester
from strategies.pivot_confluence import PivotConfluenceStrategy

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["backtest"], default="backtest")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    bt = Backtester(cfg)
    results = bt.run(PivotConfluenceStrategy(cfg))

    print("\n=== BACKTEST SUMMARY ===")
    print(results["trades"].to_string(index=False))
    print("\n=== METRICHE ===")
    for k, v in results["metrics"].items():
        print(f"{k}: {v}")
    print("\nBy day:")
    print(results["by_day"].to_string())
    outp = "backtest_trades.csv"
    results["trades"].to_csv(outp, index=False)
    print(f"\nTrade esportati in: {outp}")

if __name__ == "__main__":
    print(">> Running: python src/main.py --mode backtest --config config.yaml")
    main()
