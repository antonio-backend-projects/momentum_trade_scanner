import argparse, yaml
from dotenv import load_dotenv
from backtest.backtest import Backtester
from strategies.pivot_confluence import PivotConfluenceStrategy

def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["backtest"], default="backtest")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    bt = Backtester(cfg)
    strat = PivotConfluenceStrategy(cfg)
    results = bt.run(strat)
    return results

if __name__ == "__main__":
    main()
