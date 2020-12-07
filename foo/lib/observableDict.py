from .observable import Observable
from collections import namedtuple

class ObservableDict(dict, Observable):
    _itemTuple = namedtuple('item', 'key value')
    _itemChangedTuple = namedtuple('item', 'key value oldValue')


    def __init__(self, *args, **kwargs):
        Observable.__init__(self)
        dict.__init__(self, *args, **kwargs)

    def popitem(self):
        keyValue = dict.popitem(self)
        self.notifyObservers(action="popitem", key=keyValue[0], item=keyValue[1])
        return keyValue

    def pop(self, key, default=None):
        value = dict.pop(self, key, default)
        self.notifyObservers(action="pop", key=key, item=value)
        return value

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.notifyObservers(action="setitem", key=key, item=value)

    def __delitem__(self, key):
        value = dict.__getitem__(self, key)
        dict.__delitem__(self, key)
        self.notifyObservers(action="delitem", key=key, item=value)

    def update(self, dict2):
        items = []
        for key, value in dict2.items():
            items.append([key, value])
        dict.update(self, dict2)
        self.notifyObservers(action="update", items=items)

    def clear(self):
        dict.clear(self)
        self.notifyObservers(action="clear")

    def _createItemTuple(self, key, value, oldValue=None):
        if oldValue == None:
            item = self._itemTuple(key=key, value=value)
        else:
            item = self._itemChangedTuple(key=key, value=value, oldValue=oldValue)
        return item

