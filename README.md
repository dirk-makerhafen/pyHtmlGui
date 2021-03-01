## PyHtmlGui

A python library for building user interfaces in html. Somewhat like reactjs, but in python.
 

##### Example 1
 
 Call python object from javascript frontend

```python
import time
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class App(Observable): pass

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        <p>i am a button calling a method of the python frontend object</p> 
        <button onclick="pyhtmlgui.call(this.get_time).then(function(e){alert(e);})">Click me</button>   
    '''
    def get_time(self):
        return time.time()

if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance  = App(),
        appViewClass = AppView,
    )
    gui.start(show_frontend=True, block=True)
```
           
##### Example 2

Update frontend automatically if python object changes

```python
import time
import threading
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

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
        I am an item that is updated when the observed backend object changes, this is the normal default way of usage  <br>
        {{ this.observedObject.value}}<br>
         <button onclick='pyhtmlgui.call(this.observedObject.pause_restart);'> {% if this.observedObject.paused == True %} Start {% else %} Pause {% endif %}</button>
    '''

if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance  = App(),
        appViewClass = AppView,
    )
    gui.start(show_frontend=True, block=True)
```
                                                                                 

#### Call python function from Js Frontend
    pyhtmlgui.call(this.function, arg1, arg2 )
"this" matches to python object that was rendered. 
 
    
Launch modes:
 1) Launch from python:
    a) python app starts server and opens Browser or Electron 
    b) python app starts server, browser or Electron must be started manually
       
 2) Launch from electron:
    
 
    
