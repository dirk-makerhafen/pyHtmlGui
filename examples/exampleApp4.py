import sys
sys.path.insert(0, ".")
import time
import threading
from pyHtmlGui import PyHtmlGui, PyHtmlView, Observable


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

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        i am a item that is updated when the observed backend object changes, this is the normal default way of usage  <br>
        {{ this.observedObject.value}}<br>
         <button onclick='pyhtmlgui.call(this.observedObject.pause_restart);'> {% if this.observedObject.paused == True %} Start {% else %} Pause {% endif %}</button>
    '''

if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance  = App(),
        appViewClass = AppView,
    )
    gui.start(show_frontend=True, block=True)
