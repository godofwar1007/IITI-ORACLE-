import json

class JargonMapper:
    def __init__(self, path: str):
        with open(path) as f:
            self.jargon_map = json.load(f)