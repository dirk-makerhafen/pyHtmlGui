import sys
sys.path.insert(0, ".")
import time
from pyHtmlGui import PyHtmlGui, PyHtmlView, Observable

class App(Observable):
    def on_frontend_ready(self, pyHtmlGuiInstance, nr_of_active_frontends):
        print("on_frontend_ready", pyHtmlGuiInstance, nr_of_active_frontends )

    def on_frontend_exit(self, pyHtmlGuiInstance, nr_of_active_frontends):
        print("frontend_disconnected", pyHtmlGuiInstance, nr_of_active_frontends )
        if nr_of_active_frontends == 0:
            exit(0)


class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        <p>i am a button calling a method of the python frontend object</p>         
        I call a python function with arguments and show its return value
      
        <button onclick="pyhtmlgui.call(this.clicked)">Click me</button>   
        <button onclick="pyhtmlgui.call(this.exit)">Exit App</button>   
    '''
    def clicked(self):
        self.call_javascript("create_random_string", ["my prefix"])(lambda x:print("Received result:", x))

    def exit(self):
        self.call_javascript("electron.exit", [], skip_results=True)


if __name__ == "__main__":
    electron_exe = sys.argv[1]

    app = App()
    gui = PyHtmlGui(
        appInstance   = app,
        appViewClass  = AppView,
        mode          = "electron",
        template_dir  = "templates",
        static_dir    = "static",
        main_html     = "window.html",
        executable    = electron_exe,
        shared_secret = "shared_secret_replace_me", # must be the same in electron pyhtmlgui.json,
        on_frontend_ready = app.on_frontend_ready,
        on_frontend_exit  = app.on_frontend_exit,

    )
    gui.start(show_frontend=True, block=True)
