import random
from pyhtmlgui import Observable, ObservableList
from .counter import Counter


class CounterInList(Observable):
    def __init__(self):
        super().__init__()
        self.counters = ObservableList()

    def add_counter(self):
        self.counters.append(Counter())

    def remove_counter(self, index):
        del self.counters[index]

    def shuffle(self):
        random.shuffle(self.counters)
