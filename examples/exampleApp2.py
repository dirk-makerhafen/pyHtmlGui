from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class App(Observable):
    def echo(self, value):
        return "echo:%s" % value

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        <p>i am a button calling a method of the python backend object with arguments</p>    
        <button onclick="pyhtmlgui.call(this.observedObject.echo, Math.random()).then(function(e){alert(e);})">Click me</button>
    '''

if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance  = App(),
        appViewClass = AppView,
    )
    gui.start(show_frontend=True, block=True)
