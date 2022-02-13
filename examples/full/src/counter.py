import threading
import time
from pyhtmlgui import Observable


class Counter(Observable):
    def __init__(self):
        super().__init__()
        self.value = 0
        self.active = True
        self.worker_thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.worker_thread.start()

    def _worker_thread(self):
        while True:
            if self.active is True:
                self.set(self.value + 1)
            time.sleep(1)

    def start(self):
        self.active = True
        self.notify_observers()

    def stop(self):
        self.active = False
        self.notify_observers()

    def set(self, value):
        self.value = value
        self.notify_observers()

    def reset(self):
        self.set(0)
