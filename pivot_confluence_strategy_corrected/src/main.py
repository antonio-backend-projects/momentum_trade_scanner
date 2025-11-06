import argparse, yaml
from backtest.backtest import Backtester
from strategies.pivot_confluence import PivotConfluenceStrategy

def load_cfg(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default='backtest')
    parser.add_argument('--config', default='config.yaml')
    args = parser.parse_args()
    cfg = load_cfg(args.config)
    if args.mode == 'backtest':
        bt = Backtester(cfg)
        strat = PivotConfluenceStrategy(cfg)
        bt.run(strat)
    else:
        print("Unsupported mode")

if __name__ == "__main__":
    main()
