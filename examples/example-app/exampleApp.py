import os
from backend import BackendAppMain
from frontend import FrontendApp
from pyHtmlGui import pyHtmlGuiGui

os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":

    backendAppMain = BackendAppMain()

    gui = pyHtmlGuiGui(
        observedObject      = backendAppMain,
        guiComponentClass   = FrontendApp,

        static_dir          = "static/",
        template_dir        = "templates/",

        main_html           = "main.html",
        electron_main_js    = "electron_main.js",

        size                = (600, 800),
        mode                = "chrome",

        exit_callback       = backendAppMain.on_gui_exit,

        #shared_secret       = "SHARED_SECRET",

        #executable=ELECTRON_COMMAND,

    )
    gui.run(startFrontend=True, block=True)
