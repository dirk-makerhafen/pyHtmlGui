import typing
import weakref


class WeakFunctionReferences:
    def __init__(self):
        self.references = {}

    def add(self, function: typing.Callable):
        # noinspection PyUnresolvedReferences
        obj = function.__self__
        fname = function.__name__
        callback_id = self._create_callback_id(function)
        wr = weakref.ref(obj, self._create_delete_callback(callback_id))
        self.references[callback_id] = (wr, fname)
        return callback_id

    def remove(self, function: typing.Callable):
        callback_id = self._create_callback_id(function)
        del self.references[callback_id]

    def get(self, callback_id: int) -> typing.Callable:
        weak_obj, fname = self.references[callback_id]
        return getattr(weak_obj(), fname)

    def get_all(self):
        callback_ids = [c for c in self.references.keys()]
        for callback_id in callback_ids:
            if callback_id in self.references.keys():
                yield self.get(callback_id)

    def _create_delete_callback(self, callback_id: int) -> typing.Callable:
        # noinspection PyUnusedLocal
        def f(wr):
            del self.references[callback_id]
        return f

    @staticmethod
    def _create_callback_id(function: typing.Callable) -> int:
        # noinspection PyUnresolvedReferences
        obj = function.__self__
        callback_id = hash("%s%s" % (id(obj), function.__name__)) & 0xffffffffffff
        if callback_id < 0:
            callback_id = callback_id * -1
        return callback_id
