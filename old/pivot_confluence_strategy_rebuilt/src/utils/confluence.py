from typing import Dict, Any

class ConfluenceScorer:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.confirms = cfg.get('universe', {}).get('confirms', {})

    def score(self, sym: str, near_map: Dict[str, bool]) -> int:
        peers = self.confirms.get(sym, [])
        return sum(1 for p in peers if near_map.get(p, False))
