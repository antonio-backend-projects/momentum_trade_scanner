import pandas as pd

def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df['high'], df['low'], df['close']
    prev_c = c.shift(1)
    tr = (h - l).abs()
    tr = pd.concat([tr, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()

def rolling_median_vol(df: pd.DataFrame, n: int = 20) -> pd.Series:
    return df['volume'].rolling(n, min_periods=1).median()

def vwap(g: pd.DataFrame) -> float:
    vol = g['volume'].astype(float)
    pv = (g['close'] * vol).sum()
    vv = vol.sum()
    return pv / vv if vv > 0 else g['close'].iloc[-1]
