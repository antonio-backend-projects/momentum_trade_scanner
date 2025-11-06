class ConfluenceScorer:
    def __init__(self, cfg):
        self.cfg = cfg
        self.map = cfg['universe'].get('confirms', {})

    def score(self, sym, near_map):
        confirms = self.map.get(sym, [])
        s = 0
        for c in confirms:
            if near_map.get(c, False):
                s += 1
        return s
