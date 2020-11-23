import sys
sys.path.insert(0, ".")
import time
import threading
from pyHtmlGui import PyHtmlGui, PyHtmlView, Observable

class App(Observable):
    pass

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        this input field is read every second by a thread in the python frontend object by calling javasript function and returning the results<br>
        <div id="target_div"><div>
    '''
    def __init__(self, observedObject, parentView):
        super().__init__(observedObject, parentView)
        self.worker_thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.worker_thread.start()

    def _worker_thread(self):
        while True:
            value = self.eval_javascript('$this.children("target_div").innerHTML = %s')()
            time.sleep(1)


if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance  = App(),
        appViewClass = AppView,
    )
    gui.start(show_frontend=True, block=True)
