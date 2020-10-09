import weakref

class Event:
    def __init__(self, action, source):
        self._action = action
        self._source = source

    @property
    def action(self):
        return self._action

    @property
    def source(self):
        return self._source


class EventMap():
    def __init__(self):
        self.events = []

    def add(self, observableObject, targetFunction):
        if type(observableObject) != weakref.ref:
            observableObject = weakref.ref(observableObject)
        if type(targetFunction) != weakref.WeakMethod:
            targetFunction = weakref.WeakMethod(targetFunction)
        self.events.append([observableObject, targetFunction])

    def attach_all(self):
        for observable, target in self.events:
            print("attach event")
            observable().attach(target())  # resolve weak references

    def detach_all(self):
        for observable, target in self.events:
            print("detach event")
            observable().detach(target())  # resolve weak references
