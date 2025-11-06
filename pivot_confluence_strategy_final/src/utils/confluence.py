from typing import Dict

class ConfluenceScorer:
    def __init__(self, cfg: Dict):
        self.cfg = cfg
        self.confirm_map = cfg['universe'].get('confirms', {})

    def score(self, symbol: str, near_map: Dict[str, bool]) -> int:
        confirms = self.confirm_map.get(symbol, [])
        return sum(int(near_map.get(s, False)) for s in confirms)
