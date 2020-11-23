import weakref

class EventSet():
    def __init__(self):
        self.events = []
    def add(self, observableObject, targetFunction):
        try:
            if not callable(observableObject.attachObserver) or not callable(observableObject.detachObserver):
                raise Exception("object type '%s' can not be observed" % type(observableObject))
        except:
            raise  Exception("object type '%s' can not be observed" % type(observableObject))

        if type(observableObject) != weakref.ref:
            observableObject = weakref.ref(observableObject)
        if type(targetFunction) != weakref.WeakMethod:
            targetFunction = weakref.WeakMethod(targetFunction)
        self.events.append([observableObject, targetFunction])

    def remove(self, observableObject, targetFunction ):
        to_remove = []
        for e in self.events:
            e_observableObject, e_targetFunction = e
            if observableObject == e_observableObject():
                if targetFunction is None or targetFunction == e_targetFunction():
                    to_remove.append(e)
        for e in to_remove:
            self.events.remove(e)

    def attach_all(self):
        for observable, target in self.events:
            try:
                observable().attachObserver(target())  # resolve weak references
            except:
                pass

    def detach_all(self):
        for observable, target in self.events:
            try:
                observable().detachObserver(target())  # resolve weak references
            except:
                pass