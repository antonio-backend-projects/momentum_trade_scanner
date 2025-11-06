import pandas as pd

def floor_pivots(prev_day: pd.DataFrame):
    H, L, C = prev_day['high'].max(), prev_day['low'].min(), prev_day['close'].iloc[-1]
    PP = (H + L + C) / 3.0
    R1 = 2*PP - L
    S1 = 2*PP - H
    R2 = PP + (H - L)
    S2 = PP - (H - L)
    return {'PP':PP, 'R1':R1, 'S1':S1, 'R2':R2, 'S2':S2}

def opening_range(df: pd.DataFrame, minutes: int = 5):
    or_df = df.head(minutes)
    return or_df['high'].max(), or_df['low'].min()

def session_slice(df: pd.DataFrame, start_ts, end_ts):
    return df[(df.index >= start_ts) & (df.index <= end_ts)]
