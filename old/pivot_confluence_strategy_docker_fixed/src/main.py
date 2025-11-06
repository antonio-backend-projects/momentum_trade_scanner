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
            print("\n=== BACKTEST SUMMARY ===")
            print(results.to_string(index=False))
            print("\nBy day:")
            print(bt.daily_pnl().to_string())

if __name__ == "__main__":
    main()
