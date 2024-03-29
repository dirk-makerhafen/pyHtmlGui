import typing
import weakref


class WeakFunctionReferences:
    def __init__(self):
        self.references = {}

    def add(self, function: typing.Callable):
        try:
            _id = id(function.__self__)
        except:
            _id = id(function)
        callback_id = (_id ^ hash(function.__name__)) & 0xffffffffffff
        if callback_id in self.references:
            return callback_id
        self.references[callback_id] = weakref.WeakMethod(function, self._create_delete_callback(callback_id))
        return callback_id

    def remove(self, function: typing.Callable):
        try:
            _id = id(function.__self__)
        except:
            _id = id(function)
        del self.references[(_id ^ hash(function.__name__)) & 0xffffffffffff]

    def get(self, callback_id: int) -> typing.Callable:
        return self.references[callback_id]()

    def get_all(self):
        return [hr for hr in [wr() for wr in self.references.values()] if hr is not None]

    def _create_delete_callback(self, callback_id: int) -> typing.Callable:
        # noinspection PyUnusedLocal
        def f(wr):
            try:
                del self.references[callback_id]
            except:
                pass
        return f
