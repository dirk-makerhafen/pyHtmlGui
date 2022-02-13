from pyhtmlgui import PyHtmlView
from .countersInDictView import CountersInDictView
from .countersInListView import CountersInListView
from .counterView import CounterView
from .twoCountersView import TwoCountersView
from .animationView import AnimationView


class AppView(PyHtmlView):
    TEMPLATE_FILE = "appView.html"

    def __init__(self, subject, parent, **kwargs):
        super().__init__(subject, parent, **kwargs)
        self.counterView = CounterView(subject=subject.counter, parent=self)
        self.counterInListView = CountersInListView(subject=subject.countersInList, parent=self)
        self.counterInDictView = CountersInDictView(subject=subject.countersInDict, parent=self)
        self.twoCounters = TwoCountersView(subject=subject.twoCounters, parent=self)
        self.animation = AnimationView(subject=subject, parent=self)

    # these functions are automatically called by pyHtmlGui if they exist in the main View class
    def on_frontend_ready(self, nr_of_connections):
        print("on_frontend_ready" , nr_of_connections)

    def on_frontend_disconnected(self, nr_of_connections):
        print("on_frontend_disconnected", nr_of_connections)
