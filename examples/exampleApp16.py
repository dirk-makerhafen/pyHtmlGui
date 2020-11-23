import sys
import os
sys.path.insert(0, ".")
import time
import subprocess
from pyHtmlGui import PyHtmlGui, PyHtmlView, Observable

class App(Observable):
    pass

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        <p>i am a button calling a method of the python frontend object</p> 
        <button onclick="pyhtmlgui.call(this.get_time).then(function(e){alert(e);})">Click me</button>   
    '''
    def get_time(self):
        return time.time()

if __name__ == "__main__":
    listen_host = "127.0.0.1"
    listen_port = 8001
    secret = "i_am_secret"
    electron_exe = sys.argv[1]

    gui = PyHtmlGui(
        appInstance=App(),
        appViewClass=AppView,
        listen_host=listen_host,
        listen_port=listen_port,
        mode="electron",
        template_dir="templates",
        static_dir="static",
        main_html="window.html",
        shared_secret=secret,  # must be the same in electron pyhtmlgui.json,
    )

    if "launch_from_within_electron" in sys.argv:
        gui.start(show_frontend=False, block=True)
    else:
        # in a deployed app, set these value in package.json and  launch electron.exe as your app so the all code below is unneccessary
        args = sys.argv.copy()
        args.append("launch_from_within_electron")
        env = os.environ.copy()
        env.update({
            "PYHTMLGUI_HOST"    : listen_host,
            "PYHTMLGUI_PORT"    : "%s" % listen_port,
            "PYHTMLGUI_SECRET"  : secret,
            "PYHTMLGUI_CMD"     : sys.executable,
            "PYHTMLGUI_CMD_ARGS": ",".join(args),
        })
        subprocess.Popen([electron_exe, gui.electron_app_dir], env=env)  # receive defaul app dir from gui and launch electron


