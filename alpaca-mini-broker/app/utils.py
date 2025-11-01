from decimal import Decimal, InvalidOperation

def to_decimal(val):
    if val is None or val == "":
        return None
    try:
        return Decimal(str(val))
    except InvalidOperation:
        return None