## PyHtmlGui

A python library for building user interfaces in html/css/js.  
Seamless and glue code free interaction between python and javascript/html. 
 
##### Example

```python
import time, datetime, threading, random
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
            self.set_value(self.value + 1)
            time.sleep(1)

    def set_value(self, value):
        self.value = value
        self.notify_observers()


# View
class CounterAppView(PyHtmlView):
    TEMPLATE_STR = '''
        Current value: {{ pyview.subject.value }} <br>
        <button onclick='pyview.subject.set_value(0);'> Reset Counter </button> <br><br>
        <button onclick="pyview.get_time().then(function(e){alert(e);})"> Get System Time </button>
        <button onclick="pyview.call_js_from_python()"> Click and watch python console </button>
        <script>
            // script tags are executed every time this view element was rendered or updated
            document.getElementById("{{pyview.uid}}").style.backgroundColor = '#'+Math.floor(Math.random()*16777215).toString(16);
        </script>
    '''

    def get_time(self):
        return "It is now: %s" % datetime.datetime.now()

    def call_js_from_python(self):
        resultsHandler = self.eval_javascript(
            script='return document.getElementById(args.uid).style.backgroundColor;',
            uid=self.uid)
        resultsHandler(callback=lambda results: print(results))
        # results = resultsHandler() #synchronous, would break eventloop here if used in a function that in itself is called from javascript
        # note multiple results if multiple frontends are connected AND PyHtmlGui.single_instance is True (the default)


# Main
if __name__ == "__main__":
    gui = PyHtmlGui(
        app_instance = CounterApp(),
        view_class   = CounterAppView,
        auto_reload  = True, # edit templates while frontend is active!
    )
    gui.start(show_frontend=True, block=True)


```
