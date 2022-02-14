import os
import time
import json
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class App(Observable):
    pass

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        <button onclick="pyview.get_time().then(function(e){alert(e);})">Get system Time</button>   
        <button onclick="pyview.ping_electron()">Ping electron process</button>   
        <div id="electron_ping_result"></div>
        <button onclick="pyview.exit()">Exit App</button>   

    '''
    def ping_electron(self):
        self.call_javascript("electron.ping",[])(self._set_result)

    def _set_result(self, values):
        self.eval_javascript("document.getElementById('electron_ping_result').innerHTML = args.value", value = json.dumps(values))

    def get_time(self):
        return time.time()

    def exit(self):
        self.call_javascript("electron.exit",[], skip_results=True) # close electron app
        exit(0)

    def on_electron_message(self, message):
        print("electron message:", message)

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

