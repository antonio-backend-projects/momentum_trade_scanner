import time
from typing import Dict
from alpaca_trade_api.rest import REST

class AlpacaBroker:
    def __init__(self, env: Dict[str,str], paper: bool = True):
        self.api = REST(env.get("APCA_API_KEY_ID"),
                        env.get("APCA_API_SECRET_KEY"),
                        base_url=env.get("APCA_API_BASE_URL"))
        self.paper = paper

    def bracket_order(self, symbol, side, qty=None, notional=None, sl_price=None, tp_price=None, tif="day"):
        params = dict(
            symbol=symbol, side=side, type="market", time_in_force=tif,
            order_class="bracket",
            take_profit={"limit_price": round(tp_price, 4)} if tp_price else None,
            stop_loss={"stop_price": round(sl_price, 4)} if sl_price else None
        )
        if qty is not None:
            params["qty"] = qty
        elif notional is not None:
            params["notional"] = notional
        else:
            raise ValueError("Provide qty or notional.")
        return self.api.submit_order(**params)

    def run_streaming(self, strategy, cfg):
        symbols = sorted(set(cfg['universe']['main'] + [s for lst in cfg['universe'].get('confirms', {}).values() for s in lst]))
        print(f"Streaming (poll) 1m bars for: {symbols}")
        while True:
            try:
                strategy.on_poll(self.api, symbols)  # demo safe
                time.sleep(10)
            except KeyboardInterrupt:
                print("Stopped.")
                break
