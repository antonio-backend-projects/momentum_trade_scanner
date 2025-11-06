import pandas as pd
import numpy as np

def atr(df: pd.DataFrame, period: int = 14):
    h, l, c = df['high'], df['low'], df['close']
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()

def rolling_median_vol(df: pd.DataFrame, period: int = 20):
    return df['volume'].rolling(period, min_periods=period).median()

def vwap(df: pd.DataFrame):
    tp = (df['high'] + df['low'] + df['close']) / 3.0
    cum_vol = df['volume'].cumsum().replace(0, np.nan)
    cum_pv = (tp * df['volume']).cumsum()
    return cum_pv / cum_vol
