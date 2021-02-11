import time
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class App(Observable):
    pass

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        <p>i am a button calling a method of the python frontend object</p> 
        <button onclick="pyhtmlgui.call(this.get_time).then(function(e){alert(e);})">Click me</button>   
    '''
    def get_time(self):
        return "This string was created by python code at %s" % time.time()

if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance  = App(),
        appViewClass = AppView,
    )
    gui.start(show_frontend=True, block=True)
