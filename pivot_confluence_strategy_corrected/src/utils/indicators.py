import pandas as pd
import numpy as np

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    close = df['close'].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()

def rolling_median_vol(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return df['volume'].rolling(period, min_periods=1).median()

def vwap(g: pd.DataFrame) -> pd.Series:
    typical = (g['high'] + g['low'] + g['close']) / 3.0
    vol = g['volume'].replace(0, np.nan)
    v = (typical * vol).cumsum() / vol.cumsum()
    return v.ffill().bfill()
