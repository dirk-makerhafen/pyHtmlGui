from .observable import Observable


class ObservableDict(dict, Observable):

    def __init__(self, *args, **kwargs):
        Observable.__init__(self)
        dict.__init__(self, *args, **kwargs)

    def popitem(self):
        key_value = dict.popitem(self)
        self.notify_observers(action="popitem", key=key_value[0], item=key_value[1])
        return key_value

    def pop(self, key, default=None):
        value = dict.pop(self, key, default)
        self.notify_observers(action="pop", key=key, item=value)
        return value

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.notify_observers(action="setitem", key=key, item=value)

    def __delitem__(self, key):
        value = dict.__getitem__(self, key)
        dict.__delitem__(self, key)
        self.notify_observers(action="delitem", key=key, item=value)

    def update(self, dict2, **kwargs):
        items = []
        for key, value in dict2.items():
            items.append([key, value])
        dict.update(self, dict2)
        self.notify_observers(action="update", items=items)

    def clear(self):
        dict.clear(self)
        self.notify_observers(action="clear")
