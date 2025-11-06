class ConfluenceScorer:
    def __init__(self, cfg):
        self.cfg = cfg
        self.confirms = cfg.get("universe", {}).get("confirms", {})

    def score(self, sym, near_map) -> int:
        friends = self.confirms.get(sym, [])
        return sum(1 for f in friends if near_map.get(f, False))
