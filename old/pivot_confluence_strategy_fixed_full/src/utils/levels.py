import pandas as pd
from typing import Tuple, Dict

def floor_pivots(prev_day: pd.DataFrame) -> Dict[str, float]:
    if prev_day is None or prev_day.empty:
        return {"PP": None, "R1": None, "S1": None}
    H = prev_day['high'].max()
    L = prev_day['low'].min()
    C = prev_day['close'].iloc[-1]
    PP = (H + L + C) / 3.0
    R1 = 2*PP - L
    S1 = 2*PP - H
    return {"PP": PP, "R1": R1, "S1": S1}

def opening_range(day_df: pd.DataFrame, minutes: int = 5) -> Tuple[float, float]:
    if day_df is None or day_df.empty:
        return None, None
    or_df = day_df.iloc[:minutes]
    return or_df['high'].max(), or_df['low'].min()
