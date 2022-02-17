from pyhtmlgui import PyHtmlGui
import os
from src.app import App
from views.appView import AppView

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":
    app = App()
    gui = PyHtmlGui(
        app_instance=app,
        view_class=AppView,
        template_dir=os.path.join(SCRIPT_DIR, "templates"),
        static_dir=os.path.join(SCRIPT_DIR, "static"),
        base_template="base.html",
        on_view_connected=app.on_view_connected,
        on_view_disconnected=app.on_view_disconnected,
        listen_port=8042,
        listen_host="127.0.0.1",
        auto_reload=True,
        single_instance=True,
        # Notice the animation and tab view in sync if you open the view in multiple browser windows
    )
    gui.start(show_frontend=True, block=True)
