from pyhtmlgui import Observable
from .counter import Counter
from .countersInDict import CounterInDict
from .countersInList import CounterInList
from .twoCounters import TwoCounters


class App(Observable):
    def __init__(self):
        super().__init__()
        self.counter = Counter()
        self.countersInDict = CounterInDict()
        self.countersInList = CounterInList()
        self.twoCounters = TwoCounters()

    def on_view_connected(self, nr_of_instances, nr_of_connections):
        print("View connected:", nr_of_instances, nr_of_connections)

    def on_view_disconnected(self, nr_of_instances, nr_of_connections):
        print("View disconnected:", nr_of_instances, nr_of_connections)
        if nr_of_instances == 0:
            print("No more frontends connected, exit now")
            exit(0)
