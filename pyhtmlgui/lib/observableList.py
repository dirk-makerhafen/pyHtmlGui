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
        self.notify_observers(action="append", index=index, item=value)

    def insert(self, index, value):
        list.insert(self, index, value)
        if index > len(self) - 1:
            index = len(self) - 1
        self.notify_observers(action="insert", index=index, item=value)

    def __setitem__(self, key, value):
        if type(key) is slice:
            index = key.start
        else:
            index = key
        old_item = list.__getitem__(self, key)
        list.__setitem__(self, key, value)
        self.notify_observers(action="setitem", index=index, old_item=old_item, new_item=value)

    def __delitem__(self, i):
        if isinstance(i, slice):
            index = i.start
        else:
            index = i
        item = list.__getitem__(self, i)
        list.__delitem__(self, i)
        self.notify_observers(action="delitem", index=index, item=item)

    def extend(self, seq):
        insert_index = len(self)
        list.extend(self, seq)
        self.notify_observers(action="extend", index=insert_index, items=seq)

    def pop(self, index=-1):
        removed_index = index
        if index == -1:
            removed_index = len(self) - 1
        value = list.pop(self, index)
        self.notify_observers(action="pop", index=removed_index, item=value)
        return value

    def remove(self, obj):
        index = self.index(obj)
        list.remove(self, obj)
        self.notify_observers(action="remove", index=index, item=obj)

    def sort(self, **kwargs):
        list.sort(self, **kwargs)
        self.notify_observers(action="sort")

    def reverse(self):
        list.reverse(self)
        self.notify_observers(action="reverse")
