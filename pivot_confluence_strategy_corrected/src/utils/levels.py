import pandas as pd

def floor_pivots(prev_day_df: pd.DataFrame):
    H = prev_day_df['high'].max()
    L = prev_day_df['low'].min()
    C = prev_day_df['close'].iloc[-1]
    PP = (H + L + C) / 3.0
    R1 = 2*PP - L
    S1 = 2*PP - H
    return {'PP': PP, 'R1': R1, 'S1': S1}

def opening_range(day_df: pd.DataFrame, minutes: int = 5):
    if len(day_df) == 0:
        return None, None
    first = day_df.iloc[:minutes]
    return first['high'].max(), first['low'].min()
