import time
import threading
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable
from exampleApp17Import import AppView

class App(Observable):
    def __init__(self):
        super().__init__()
        self.value = 0
        self.paused = False
        self.worker_thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.worker_thread.start()

    def _worker_thread(self):
        while True:
            if self.paused is False:
                self.value = time.time()
                self.notifyObservers()
            time.sleep(1)

    def pause_restart(self):
        self.paused = not self.paused
        self.notifyObservers()


if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance  = App(),
        appViewClass = AppView,
        auto_reload=True
    )
    gui.start(show_frontend=True, block=True)
