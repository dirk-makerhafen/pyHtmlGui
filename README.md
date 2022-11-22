# PyHtmlGui

[![PyPI version](https://img.shields.io/pypi/v/PyHtmlGui?style=for-the-badge)](https://pypi.org/project/pyhtmlgui/)
[![PyPi Downloads](https://img.shields.io/pypi/dm/PyHtmlGui?style=for-the-badge)](https://pypistats.org/packages/pyhtmlgui)
![Python](https://img.shields.io/pypi/pyversions/PyHtmlGui?style=for-the-badge)
[![License](https://img.shields.io/pypi/l/PyHtmlGui.svg?style=for-the-badge)](https://pypi.org/project/PyHtmlGui/)


PyHtmlGui is a Python library for creating fast, easy to build, HTML/JS user interfaces 
with seamless interaction between Python and Javascript/HTML.

PyHtmlGui is designed to take the hassle out of writing GUI applications.
It allows python developers to write beautiful, modern and fast HTML user interfaces without 
any boilerplate code and with minimal javascript knowledge.  

PyHtmlGui enables seamless function calls from Javascript to Python and the reverse, including asynchronous return values from one language to the other.
It creates reactive user interfaces by following the observer pattern to automatically update the HTML frontend if the underlying python model changes. 

PyHtmlGui is inspired by Python [eel](https://github.com/ChrisKnott/Eel) and Javascript [React](https://reactjs.org/).

If you are familiar with Python and HTML, probably just jump to
[Minimal App](#minimal-app) below, or dive right into  this [example code](https://github.com/dirk-makerhafen/pyHtmlGui/tree/master/examples/full) 
that shows most functions of PyHtmlGui in one simple app. 



Example app screenshot:
<p align="center"><img src="https://raw.githubusercontent.com/dirk-makerhafen/pyHtmlGui/master/examples/full/screenshot.png"></p>


<!-- TOC -->

- [PyHtmlGui](#pyhtmlgui)
- [Install](#install)
- [Minimal App](#minimal-app)
- [Directory Structure](#directory-structure)
- [PyHtmlGui Options](#pyhtmlgui-options)
- [PyHtmlGui Methods](#pyhtmlgui-methods)
- [Calling Python from Javascript](#calling-python-from-javascript)
- [Calling Javascript from Python](#calling-javascript-from-python)
- [PyHtmlView methods](#pyhtmlview-methods)
- [PyHtmlView render customisation](#pyhtmlview-render-customisation)
- [Using from inside Electron](#using-from-inside-electron)
- [Renderer details](#renderer-details)

<!-- /TOC -->


### Install

Install from pypi with `pip`:

```shell
pip install pyhtmlgui
```


### Minimal App

A PyHtmlGui app is split into your normal python application, and PyHtmlGui view classes.

##### App Logic
First create your app logic, make your classes inherit from **`pyhtmlgui.Observable`** 
and call **`notify_observers()`**  when your data changes. 

```python
import time, datetime, threading, random
from pyhtmlgui import Observable

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
```

##### View
Create a simple view with some inline html template.
Note the **`pyview`** reference used in the template. **`pyview`** represents
the PyHtmlView object instance that belongs to the tempate, **`pyview.subject`** is the app instance observed by that view.

```python
import datetime
from pyhtmlgui import PyHtmlView

class CounterAppView(PyHtmlView):
    TEMPLATE_STR = '''
        Current value: {{ pyview.subject.value }} <br>
        <button onclick='pyview.subject.set_value(0);'> Reset Counter </button> <br><br>
        <button onclick="pyview.get_time().then(function(e){alert(e);})"> Get System Time </button>
    '''

    def get_time(self):
        return "It is now: %s" % datetime.datetime.now()
```

##### Starting the app
```python
from pyhtmlgui import PyHtmlGui
gui = PyHtmlGui(
    app_instance = CounterApp(),
    view_class   = CounterAppView,
)
gui.start(show_frontend=True, block=True)
```
This will start a webserver on the default settings (http://localhost:8000) and open a browser to http://localhost:8000/.


### Directory Structure

A larger PyHtmlGui application will be split into templates consisting of various web-technology files (.html, .js, .css), 
and various Python scripts split into actual app logic and views.

```
app/    <- App logic
  app.py
views/  <- Python views
  appView.py
templates/      <- Template files
  base.html     <- Extend pyHtmlGuiBase.html from pyhtmlgui assets/templates/
  appView.html  <- TEMPLATE_FILE for appView class
static/         <- Static content, add what you need
  css/app.css
  js/app.js
run.py
```

JS/CSS files are included by the apps base template. By default this is *pyHtmlGuiBase.html* from *pyhtmlgui/assets/templates*.
To extend this file and load your custom css/js, create a html file in your template dir and set matching options when initializing PyHtmlGui.

*templates/base.html*
```html
{% extends 'pyHtmlGuiBase.html' %}

{% block head_scripts %}
    <script src="/static/js/app.js"></script>
{% endblock %}

{% block head_css %}
    <link rel="stylesheet" href="/static/css/app.css">
{% endblock %}

{% block head_meta %}
    <title>PyHtmlGui Example App</title>
{% endblock %}
```

*templates/appView.html*
```html
<p>Hello World</p>
```

*views/appView.py*
```python
class AppView(pyHtmlView):
    TEMPLATE_FILE = "appView.html"
```

*run.py*
```python
gui = PyHtmlGui(
    ...
    base_template = "base.html",
    template_dir  = "templates",
    static_dir    = "static"
)
gui.start()
```


### PyHtmlGui Options

Additional options can be passed to the PyHtmlGui constructor as keyword arguments.

  - **app_instance**: 
        Your main App logic object
  - **view_class**: 
        A class that Inherits from PyHtmlView
  - **static_dir**: 
        Static files like js/css and fonts go here *Default: `''`*
  - **template_dir**: 
        Templates used in views go here *Default: `''`*
  - **electron_app_dir**: 
        If browser is electron, this directory should contain electrons main.js *Default: `None`*
  - **base_template**: 
        A file in *template_dir* extending pyHtmlGui/assets/templates/pyHtmlGuiBase.html,  *Default: `None`*
  - **on_view_connected**: 
        This Callback function is called when a frontend connects via websocket. Arguments passed: "nr of view instances", "nr of websocket connections" *Default: `None`*
  - **on_view_disconnected**: 
        This Callback function is called when a frontend disconnects via websocket. Arguments passed: "nr of view instances", "nr of websocket connections" *Default: `None`*
  - **size**: 
        A tuple of ints specifying the (width, height) of the main window in pixels *Default: `None`*
  - **position**: 
        A tuple of ints specifying the (X, Y) position of the main windows in pixels.  *Default: `None`*
  - **browser**: 
        A string specifying what browser to use (e.g. `'default'`, `'chrome'`, `'chrome'`, `'electron'`). `'default'` opens your systems default browser. *Default: `'default'`*.
  - **executable**: 
        Path to browser executable, if needed.
  - **listen_host**: 
        A string specifying what hostname to use for the server. *Default: `'localhost'`)*   
  - **listen_port**:
        An int specifying what port to use for the server.  *Default: `8000`*.    
  - **shared_secret**: 
        Add a security token to prevent unauthorized access to the webserver, use "" to automatically generate internally, None to disable token *Default: `None`*.
  - **auto_reload**: 
        For development, monitor templates and reload while app is running. *Default: `False`*.
  - **single_instance**: 
        Create only one view instance and share it between all connected websockets. 
        Try examples/full app and notice the animation and tab view in sync between multiple browser windows. *Default: `True`*.


### PyHtmlGui Methods

PyHtmlGui has only 4 relevant public methods:

- PyHtmlGui.**__init\__(\*\*kwargs)**:  
   Create a new PyHtmlGui instance. See list above for detailed description of **`kwargs`**
    
- PyHtmlGui.**start(show_frontend, block)**:  
   Launch PyHtmlGui websocket server. If **`show_frontend`** is *true*, the browser defined on **`__init__`** will be started.
   If **`block`** is *true* this call will block until the server exits.
    
- PyHtmlGui.**stop()**:
   Stop PyHtmlGui server, this will release a blocking **`start`** call.

- PyHtmlGui.**show()**: 
    Launch browser defined on **`__init__`**.


### Calling Python from Javascript

Html/JS rendered by a View can use the **`pyview`** reference to access the python side view object.
Note that the **`pyview`** object is not available from javascript at runtime, 
**`pyview.`** is replaced by a dynamic function reference when the view is rendered. See [Renderer details](#renderer-details) for more.

```python
class myView(pyHtmlView):
    TEMPLATE_STR = '''
        <button onclick='pyview.addSome(23).then(function(e){alert(e);});'></button>
    '''
    def addSome(self, value):
        return value + 42
```


### Calling Javascript from Python

You can call javasript functions from inside the python view object and receive the return values.
If multiple frontends are connected to a shared view, you will get one result for each active frontend. 
Use **`args`** to pass a list of arguments to the called JS function if needed.

```python
class myView(pyHtmlView):
    def call_js_async(self):
        resultsHandler = self.call_javascript(js_function_name="Math.round", args=[1.2345] )
        resultsHandler(callback=lambda results: print(results))

    def call_js_sync(self):
        resultsHandler = self.call_javascript(js_function_name="Math.round", args=[1.2345] )
        print(resultsHandler())
```

You can also eval javascript code dynamically.  
Keyword arguments passed to **`eval_javascript`** are available as **`args`** array inside the evaled Javascript.
 
```python
class myView(pyHtmlView):
    TEMPLATE_STR = '''
        Hello world
        <script>
            document.getElementById("{{pyview.uid}}").style.backgroundColor = '#'+Math.floor(Math.random()*16777215).toString(16);
        </script>
    '''
    def eval_js_async(self):
        resultsHandler = self.eval_javascript(
            script='return document.getElementById(args.uid).style.backgroundColor;',
            uid=self.uid)
        resultsHandler(callback=lambda results: print(results))
```


### PyHtmlView methods

All your views should inherit from PyHtmlView. 
PyHtmlView observes your python app logic object(s) and provides rendering methods as well 
as event and javascript handling. 

```python
class AppSub(Observable):
    def __init__(self):
        self.value = 23

class App(Observable):
    def __init__(self):
        self.appSub = AppSub()
    
class AppSubView(PyHtmlView):
    TEMPLATE_STR = '{{pyview.subject.value}}'

class AppView(PyHtmlView):
    TEMPLATE_STR = '''Some Subview: {{pyview.subview.render()}}'''

    def __init__(self, subject, parent, **kwargs):
        super().__init__(subject, parent, **kwargs)
        self.subview = AppSubView(subject.appSub, self)
```


- PyHtmlView.**__init\__(subject, parent)**  
    Create a new view instance, attaches default event that observes the **`subject`** and calls
    **`_on_subject_updated()`** when the subject notifies its observers.
    To prevent attaching of the default event, overwrite **`_on_subject_updated`** to None.
    Use **`parent`** in nested views to access the **`parent`** view that contains this element.
    **`parent`** also keeps track of visible/invisible elements and attaches/detached events appropriatley.
    
    
- PyHtmlView.**render()**  
    Returns the rendered template string as markup element. It can be use in other templates via
    **`{{pyview.subview.render()}}`** to create nested views.

- PyHtmlView.**update()**  
    Update the DOM element in place. View must have been rendered before and be visible in the DOM.
    By default, this function is called from **`_on_subject_updated`** when the observed **`subject`** changes and the view is visible.

- PyHtmlView.**call_javascript(fname, args, skip_results)**  
    Call frontend javascript function **`fname`**. Supply a list of args if needed.
    If **`skip_results`** is **`true`** no results will be received, and **`None`** will be returned.
    Otherwise a **`JavascriptCallResult`**  object will be returned. Results can be received either 
    asynchronous via javascriptCallResult(callback=lambda results:print(results)) or 
    synchronous via result = javascriptCallResult()
  
- PyHtmlView.**eval_javascript(script, skip_results, \*\*kwargs)**  
   Dynamically eval javascript in frontend. Behaves largely like call_javascript, but kwargs are passed as **`args`** variable to the javascript call.
   **eval_javascript(script='return 42 + args.value', value=23)**
   
- PyHtmlView.**set_visible(visible)**  
    This method is called right before the view is rendered and added to the DOM, 
    or after a parent element was rendered and this view is no longer visible.
    It attaches/detaches events based on visibility. Overwrite this function if you need 
    your view to react to weather its visible or not.
    
- PyHtmlView.**add_observable(subject, target_function)**   
    Add a new event to this view that is active as long as the view is visible.
    By default, **`__init__`** will assign target_function **`_on_subject_updated`** to 
    **`subject`**. If you not set target_function the default target function **`_on_subject_updated`** will be used.
    Use this function if you want your view to react to multiple model objects.
    
- PyHtmlView.**remove_observable(subject, target_function)**  
    Remove event from view.
    
- PyHtmlView.**_on_subject_updated(source, \*\*kwargs)**  
   This is the default event handler for **`self.subject`**, it will call **`update`** to redraw the DOM element

- PyHtmlView.**_on_subject_died(self, wr)**   
  This is called when the  **`self.subject`** object is derefered. The default handler removes the 
  view from DOM, detaches all events and destroys the view object including all its children.
  


### PyHtmlView render customization

Your view classes that inherit from PyHtmlView have several options to customize how their 
container is rendered.

```python
class myView(PyHtmlView):
    TEMPLATE_STR = "test"
```
will render 
```html
<div class="myView" id="pvf6p3p7uiirkwac40">test</div>
```
You can change how the element is rendered by setting some attributes of your view class.
To remove the class attribute, set **`DOM_ELEMENT_CLASS`**  to **`None`**.

```python
class myView(PyHtmlView):
    DOM_ELEMENT = "p"
    DOM_ELEMENT_CLASS = "myFoo myBar"
    DOM_ELEMENT_EXTRAS = 'style="color:red;"'
    TEMPLATE_STR = "test"
```
rendered html:
```html
<p class="myFoo myBar" style="color:red;" id="pvf6p3p7uiirkwac40">test</p>
```

You can make DOM_ELEMENT, DOM_ELEMENT_CLASS and DOM_ELEMENT_EXTRAS dynamic, so they are applied every time the dom element is updated.
This does not work for TEMPLATE_STR because the template is prepared once and cached.
```python
class myView(PyHtmlView):
    TEMPLATE_STR = "test"

    @property
    def DOM_ELEMENT_EXTRAS(self):
        color = "%s" % "".join(random.choices("456789abcdef", k=3))
        return 'style="color:#%s"' %  color
```


### Using from inside Electron

Make electron launch your python app so you can create a shippable electron executable
what runs your python application logic + views!
Full code for the example below is available [on github](https://github.com/dirk-makerhafen/pyHtmlGui/tree/master/examples/electron) 

Electron directory Structure
```
app.py  <- Your python app logic
main.js <- Minimal electron main
package.json <- Electron package.json + shared pyhtmlgui config
pyhtmlgui.js <- Copy of assets/electron/pyhtmlgui.js
```

While you can download *main.js*, *package.json*, *pyhtmlgui.js* from github, you can also receive them from PyHtmlGui if its installed via pip.
Create a minimal PyHtmlGui instance, set **`electron_app_dir`** to your target folder. Running this script will copy
 *package.json*, *pyhtmlgui.js* and an example  *main.js* to your **`electron_app_dir`**, if they don't exist. 

```
from pyhtmlgui import PyHtmlGui
PyHtmlGui(None, None, electron_app_dir = "mydir")
```

*package.json*, with additional options for PyHtmlGui.
```
{
  "name": "Example App",
  "main": "main.js",
  "PYHTMLGUI_HOST": "127.0.0.1",
  "PYHTMLGUI_PORT": 8023,
  "PYHTMLGUI_SECRET" : "shared_secret_replace_me",
  "PYHTMLGUI_CMD" : "python",
  "PYHTMLGUI_CMD_ARGS" : "app.py"
}
```

*main.js* (shortend, full version in examples/electron/main.js)
```javascript
const pyhtmlgui = require('./pyhtmlgui.js');

pyhtmlgui.start(); // start python process early

app.on('ready', () => {
  pyhtmlgui.init_ipc();
  // TODO create window
  mainWindow.loadURL(pyhtmlgui.get_start_url());
})

pyhtmlgui.add_public_functions({
  exit: function (){
    app.quit();
    app.exit(0);
  },
  ping: function (){
    return "Pong from electron";
  }
})
```

*app.py* is launched automatically from inside electrons main process. 
Note the usage of **`self.call_javascipt("electron.ping")`**. 
Javascript calls from python prefixed with **`electron.`** are automaticlly forwarded to functions declared 
in electrons *main.js* via **`pyhtmlgui.add_public_functions(..).`**

*app.py*
```python
import os, time, json
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class App(Observable): # empty app logic
    pass

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        <button onclick="pyview.ping_electron()">Ping electron process</button>   
        <div id="electron_ping_result"></div>
        <button onclick="pyview.exit()">Exit App</button>   
    '''
    def ping_electron(self):
        self.call_javascript("electron.ping",[])(self._set_result)

    def _set_result(self, values):
        self.eval_javascript("document.getElementById('electron_ping_result').innerHTML = args.value", skip_results=True, value = json.dumps(values))

    def exit(self):
        self.call_javascript("electron.exit",[], skip_results=True) # close electron app, no results to receive
        exit(0)

if __name__ == "__main__":
    package_json = json.loads(open(os.path.join(os.path.dirname(__file__), "package.json"), "r").read()) # so electron and we use the same values
    gui = PyHtmlGui(
        browser          = "electron",
        app_instance     = App(),
        view_class       = AppView,
        listen_host      = package_json["PYHTMLGUI_HOST"],
        listen_port      = package_json["PYHTMLGUI_PORT"],
        shared_secret    = package_json["PYHTMLGUI_SECRET"],
    )
    gui.start(show_frontend=False, block=True)
``` 



### Renderer details

Templates are jinja2 templates. **`pyview`** is the python view object passed to the jinja renderer. 
Default jinja rendering rules apply. **`"{{pyview.variable}}"`** will render a variable, 
**`"{{pyview.myfunction()}}"`** will run myfunction at render time and show its results. 
**`"{{pyview.subject}}"`** gives access to the app logic object observed to this view. 

If you use **`pyview.`** outside of jinjas tags, some pyHtmlGui magic will be applied:   


```python
class myView():
    TEMPLATE_STR = '''
        <button onclick="pyview.addOne({{pyview.addOne(1)}}).then(function(e){alert(e);})">
        </button>
    '''
    def addOne(self, value):
        return value + 1
```


At the first rendering step, the convinience function notion will be replaced with something the jinja template renderer can use:
```html
<button onclick="pyhtmlgui.call({{_create_py_function_reference(pyview.addOne)}}, {{pyview.addOne(1)}}).then(function(e){alert(e);})"></button>
```
After the final render this is the actual content that is send to the browser. The inner **`pyview.addOne`** function has been resolved at render 
time, and some magic function reference has been created in the background to access the outer **`pyview.addOne`** function later.
```html
<button onclick="pyhtmlgui.call(24325642347682, 2).then(function(e){alert(e);})"></button>
```
After this, clicking the button will show "3"
