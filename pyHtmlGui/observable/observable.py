from ..lib import WeakFunctionReferences

class Observable:
    def __init__(self):
        self._observers =  WeakFunctionReferences()

    def attachObserver(self, observer):
        self._observers.add(observer)

    def detachObserver(self, observer):
        self._observers.remove(observer)

    def notifyObservers(self, *args, **kwargs):
        for eventObserver in self._observers.get_all():
            eventObserver(kwargs)

