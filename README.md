## PyHtmlGui

A python library for building user interfaces in html. Somewhat like reactjs, but in python.
Seamless and glue code free interaction between python and javascript/html. 
 
##### Example

```python
import time, datetime
import threading
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable
# App Logic
class CounterApp(Observable):
    def __init__(self):
        super().__init__()
        self.value = 0
        self.worker_thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.worker_thread.start()

    def _worker_thread(self):
        while True:
            self._set_value(self.value + 1)
            time.sleep(1)

    def _set_value(self, value):
        self.value = value
        self.notify_observers()

    def reset(self):
        self._set_value(0)


# View
class CounterAppView(PyHtmlView):
    TEMPLATE_STR = '''
        Current value: {{ pyview.subject.value }} <br>
        <button onclick='pyview.subject.reset();'> Reset Counter </button> <br><br>
        <button onclick="pyview.get_time().then(function(e){alert(e);})"> Get System Time </button>          
    '''
    def get_time(self):
        return "It is now: %s" % datetime.datetime.now()

# Main
if __name__ == "__main__":
    app = CounterApp()
    gui = PyHtmlGui(
        app_instance = app,
        view_class   = CounterAppView,
        listen_port  = 8001,
        listen_host  = "0.0.0.0",
    )
    gui.start(show_frontend=True, block=True)

```
