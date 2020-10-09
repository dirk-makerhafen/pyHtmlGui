## PyHtmlGui

A python library for building user interfaces

### Example

```python
import os, threading, time
from pyHtmlGui import pyHtmlGui, pyHtmlGuiComponent
from pyHtmlGui.observable.observable import Observable

class Example1_App(Observable):
    def __init__(self):
        super().__init__()
        self.current_timestamp = None
        self.updateThread = threading.Thread(target=self._update_thread)
        self.updateThread.start()
        
    def _update_thread(self):
        while True:
            self.current_timestamp = time.time()
            self.notifyObservers()
            time.sleep(1)



class Example1_Gui(pyHtmlGuiComponent):
    TEMPLATE_STR = '''
        <p style="text-align:center"> {{ this.observedObject.current_timestamp }} </p>
    '''

if __name__ == "__main__":
    example1_App = Example1_App()
    gui = pyHtmlGui(
        observedObject      = example1_App,
        guiComponentClass   = Example1_Gui,
    )
    gui.run()
```
                                                                                        

#### Call python function from Js Frontend
    pyHtmlGui.call({{ py(this.func)}}, 1,2,3 ) 
#### Call JS function from Python GUI class    
    $this is replace with jquery selector for current component
    js = '$this.find( ".row" ).css( "background-color", "blue" );'
    self.javascript_call(js)

this is component instance

call javascrip from Component

    jsf = 'return 2+2;'
    self.javascript_call(jsf, callback=lambda result:print(result) )

    #jsf = 'return 4+2;'
    #r = self.javascript_call(jsf )() # this will block and fail at this point because this function is called from javascript and the js loop is waiting for the result of this function
    #print("result:", r)
    
    
How to make your objects observable by pyHtmlGui:
A) If you already have some eventsystem that created an event or calls a 
callback if an object is updates:

class YourEventSystem():
    def send_event(datadict):
       callbackobject.send()
        pass # example only
    def add(callbackobject):
        pass
    def remove(callbackobject):
        pass #
class yourclass(YourEventSystem):
    def __init__(self):
        self.value = 0
    def set_value(value):
        self.value = value
        self.send_event({"type": "update", "parameter": "value"})

B) If you don't have events:
have you internal objects extend Observable, and call self.notifyObservers() when you do an update to the object

import pyHtmlGui.observable.Observablue

class yourclass(Observablue):
    def __init__(self):
        self.value = 0
    def set_value(value):
        self.value = value
        self.notifyObservers()
