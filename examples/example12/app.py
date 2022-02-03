import os
import time
import json
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class App(Observable):pass

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        <p>i am a button calling a method of the python frontend object</p> 
        <button onclick="pyhtmlgui.call(this.get_time).then(function(e){alert(e);})">Click me</button>   
        <button onclick="pyhtmlgui.call(this.ping)">get electron process info</button>   
        <div id="electron_ping_result"><div>
    '''
    def ping(self):
        self.call_javascript("electron.ping",[])(self.set_result)

    def set_result(self, values):
        self.eval_javascript("document.getElementById('electron_ping_result').innerHTML = args.value", value = json.dumps(values))

    def get_time(self):
        return time.time()

def _exit():
    print("FRONTEND EXIT CALLBACK")
    exit(0)

if __name__ == "__main__":
    package_json = json.loads(open(os.path.join(os.path.dirname(__file__),"package.json"),"r").read()) # so electron and we use the same values
    gui = PyHtmlGui(
        mode = "electron",
        appInstance  = App(),
        appViewClass = AppView,
        listen_host  = package_json["PYHTMLGUI_HOST"],
        listen_port   = package_json["PYHTMLGUI_PORT"],
        shared_secret = package_json["PYHTMLGUI_SECRET"],
        on_frontend_exit=_exit
    )
    gui.start(show_frontend=False, block=True)

