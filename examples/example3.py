from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable
#Shows some ways how to call pythons functions from javascript
import time

class App(Observable):
    def ping(self):
        return "Pong: %s" % time.time()
    def echo(self, value):
        return "From model object: %s" % value

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        <p>i am a button calling a method of the python backend object with arguments</p>    
        <button onclick="pyhtmlgui.call(this.observedObject.echo, Math.random()).then(function(e){alert(e);})">Click me</button>
    '''
    def echo(self, value):
        return "From view object: %s" % value

if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance  = App(),
        appViewClass = AppView,
    )
    gui.start(show_frontend=True, block=True)
