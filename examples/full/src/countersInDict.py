import uuid
from pyhtmlgui import Observable, ObservableDict
from .counter import Counter


class CounterInDict(Observable):
    def __init__(self):
        super().__init__()
        self.counters = ObservableDict()

    def add_counter(self):
        name = ("%s" % uuid.uuid4()).split("-")[0]
        self.counters[name] = Counter()

    def remove_counter(self, name):
        del self.counters[name]
