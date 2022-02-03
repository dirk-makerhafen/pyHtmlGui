## PyHtmlGui

A python library for building user interfaces in html. Somewhat like reactjs, but in python.
 
##### Example

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
                self.notify_observers()
            time.sleep(1)

    def pause_restart(self):
        self.paused = not self.paused
        self.notify_observers()

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        I am an item that is updated when the observed backend object changes, this is the normal default way of usage  <br>
        {{ this.observedObject.value}}<br>
        <button onclick='pyhtmlgui.call(this.observedObject.pause_restart);'> {% if this.observedObject.paused == True %} Start {% else %} Pause {% endif %}</button>
        
'''

if __name__ == "__main__":
    gui = PyHtmlGui(
        app_instance  = App(),
        view_class = AppView,
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
    
 
    
#### Examples

### Example 1
This is a simple app example. 
It has:
    - 1 View Class
    - 1 App Object
    - Updates the frontend automatically when the app object changes
    - Calls a function in the App object from a html button.
    
### Example 3
Shows some ways how to call pythons functions from javascript

### Example 4
Shows some ways how to call javascript code from python

### Example 5
Normally frontend object are updated when notifyObservers() is called and the object is visible.
However sometimes you might want to overwrite this. For example if you want to do some frontend animation controlled by python
, you might want to render the object once and then update for example only some css style variable. 
To do this overwrite the _on_observedObject_updated of your PyHtmlView object

### Example 6
If you want to render a list or dict of objects, there are helper classes that keep the frontend in sync with the backend object.

### Example 7
Obviously you don't have the put the template html into the python file.
Example 7 show how to put everything in seperate directorys.
Also enables auto reload to you can keep you app running while editing html. changed will automatically be show in the gui.

### Example 9
Frontend object are only updated, aka the notifyObservers() event is only processed if the object is visible.
Example 9 showcases this.

### Example 10
If you want to show multiple frontend views for one app instance, 
you can choose if all fontend share one state or if you want independant frontend instances.

### Example 11
You can also use electron as a frontend. You can choose you launch order. 
You can either: Launch you python code, this code will then launch electron to show your frontend.


### Example 12
Or: Launch an electron app that imports pyhtmlgui that will than launch you python code from inside the electron app.

