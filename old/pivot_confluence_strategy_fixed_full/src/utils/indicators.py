import pandas as pd
import numpy as np

def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    high, low, close = df['high'], df['low'], df['close']
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=1).mean()

def rolling_median_vol(df: pd.DataFrame, n: int = 20) -> pd.Series:
    return df['volume'].rolling(n, min_periods=1).median()

def vwap(g: pd.DataFrame) -> pd.Series:
    pv = (g['high'] + g['low'] + g['close']) / 3.0
    cum_pv = (pv * g['volume']).cumsum()
    cum_vol = g['volume'].cumsum().replace(0, np.nan)
    return (cum_pv / cum_vol).ffill()
