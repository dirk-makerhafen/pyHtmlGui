import weakref

class WeakFunctionReferences():
    def __init__(self):
        self.references = {}

    def add(self, function):
        obj = function.__self__
        fname = function.__name__
        callback_id = self._get_callback_id(function)
        wr = weakref.ref(obj, self._obj_died(callback_id))
        self.references[callback_id] = (wr, fname)
        return callback_id

    def remove(self, function):
        callback_id = self._get_callback_id(function)
        del self.references[callback_id]

    def get(self, callback_id):
        wr, fname  = self.references[callback_id]
        obj = wr()
        f = getattr(obj, fname)
        return f

    def get_all(self):
        keys = [key for key in self.references.keys()]
        for key in keys:
            if key in self.references.keys():
                yield self.get(key)

    def _obj_died(self, callback_id ):
        def f(wr):
            print("object died", callback_id, wr)
            del self.references[callback_id]
        return f

    def _get_callback_id(self, function):
        obj = function.__self__
        callback_id = hash("%s%s" % (id(obj), function.__name__)) & 0xffffffffffff
        if callback_id < 0:
            callback_id = callback_id * -1
        return callback_id

