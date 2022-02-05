from pyhtmlgui import PyHtmlGui
import os
from .src.app import App

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":
    app = App()
    gui = PyHtmlGui(
        app_instance    = app,
        view_class      = AppView,
        template_dir    = os.path.join(SCRIPT_DIR, "templates"),
        static_dir      = os.path.join(SCRIPT_DIR, "static"),
        base_template   = "base.html",
        listen_port     = 8888,
        listen_host     = "127.0.0.1",
        auto_reload     = True,
        shared_secret   = None,
    )
    httpEndpoints = HttpEndpoints(app, gui)
    gui.start(show_frontend=False, block=True)




