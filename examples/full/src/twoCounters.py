from pyhtmlgui import Observable
from .counter import Counter


class TwoCounters(Observable):
    def __init__(self):
        super().__init__()
        self.counter1 = Counter()
        self.counter2 = Counter()
