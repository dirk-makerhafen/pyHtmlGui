from .observable import Observable

class ObservableList(list, Observable):

    def __init__(self, *args, **kwargs):
        Observable.__init__(self)
        list.__init__(self, *args, **kwargs)

    def __iadd__(self, other):
        self.extend(other)
        return self

    def append(self, value):
        index = len(self)
        list.append(self, value)
        self.notifyObservers(action="append", index=index, item=value)

    def insert(self, index, value):
        list.insert(self, index, value)
        if index > len(self) - 1:
            index = len(self) - 1
        self.notifyObservers(action="insert", index=index, item=value)

    def __setitem__(self, key, value):
        if (type(key) is slice):
            index = key.start
        else:
            index = key
        oldItem = list.__getitem__(self, key)
        list.__setitem__(self, key, value)
        self.notifyObservers(action="setitem", index=index, oldItem=oldItem, newItem=value)

    def __delitem__(self, i):
        if isinstance(i, slice):
            index = i.start
        else:
            index = i
        item = list.__getitem__(self, i)
        list.__delitem__(self, i)
        self.notifyObservers(action="delitem", index=index, item=item)

    def extend(self, seq):
        insertIndex = len(self)
        list.extend(self, seq)
        self.notifyObservers(action="extend", index=insertIndex, items=seq)

    def pop(self, index=-1):
        removedIndex = index
        if (index == -1):
            removedIndex = len(self) - 1
        value = list.pop(self, index)
        self.notifyObservers(action="pop", index=removedIndex, item=value)
        return value

    def remove(self, obj):
        index = self.index(obj)
        list.remove(self, obj)
        self.notifyObservers(action="remove", index=index, item=obj)

    def sort(self, **kwargs):
        list.sort(self, **kwargs)
        self.notifyObservers(action="sort")

    def reverse(self):
        list.reverse(self)
        self.notifyObservers(action="reverse")
