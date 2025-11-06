import pandas as pd

def floor_pivots(df: pd.DataFrame) -> dict:
    if df.empty:
        return {'PP': None, 'R1': None, 'S1': None}
    H = df['high'].max()
    L = df['low'].min()
    C = df['close'].iloc[-1]
    PP = (H + L + C) / 3.0
    R1 = 2*PP - L
    S1 = 2*PP - H
    return {'PP': PP, 'R1': R1, 'S1': S1}

def opening_range(df: pd.DataFrame, minutes: int = 5):
    g = df.iloc[:minutes]
    return g['high'].max(), g['low'].min()
