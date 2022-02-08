import typing
from .weakFunctionReferences import WeakFunctionReferences


class Observable:
    def __init__(self):
        self._observers = WeakFunctionReferences()

    def attach_observer(self, target_function: typing.Callable) -> None:
        self._observers.add(target_function)

    def detach_observer(self, target_function: typing.Callable) -> None:
        self._observers.remove(target_function)

    def notify_observers(self, **kwargs) -> None:
        for target_function in self._observers.get_all():
            target_function(self, **kwargs)
