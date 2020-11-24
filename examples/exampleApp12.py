import time
import threading
import random
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class App(Observable):
    def __init__(self):
        super().__init__()
        self.app_identifier = random.randint(0,100000)
        self.app_value = self.app_identifier
        self.connected_view_feedback = {}

        self.worker_thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.worker_thread.start()

    def _worker_thread(self):
        while True:
            self.app_value += 1
            self.notifyObservers()
            time.sleep(1)

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        if you set shared_instance = True, there will only one appview for all connected clients, 
        so if you open multiple browser windows you will see the AppView id is the same in all views and all views show exacly the same.
        if you use shared_instance = false (the default) every connected frontend gets its own session<br>
        AppView: {{ this.appview_identifier }}, {{ this.appview_value }}<br>
        App:     {{ this.observedObject.app_identifier }}, {{ this.observedObject.app_value }}<br>
        Connected frontend feedback: {{ this.connected_frontend_feedback }}
        Connected AppView feedback: {{ this.observedObject.connected_view_feedback }}
    '''
    def __init__(self, observedObject, parentView):
        super().__init__(observedObject, parentView)
        self.appview_identifier = random.randint(0,100000)
        self.appview_value = self.appview_identifier
        self.worker_thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.worker_thread.start()
        self.connected_frontend_feedback = []

    def _worker_thread(self):
        while True:
            self.appview_value += 1
            if self.is_visible is True: # if we call update ourself, we need to check visibility, we cant update invisible components.
                self.update()
            self.call_javascript("get_frontend_id",[])(self._frontend_feedback)
            time.sleep(1)
    def _frontend_feedback(self, values): # values containes results from all connected frontends,
        self.observedObject.connected_view_feedback[self.appview_identifier] = values
        self.connected_frontend_feedback = values

if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance     = App(),
        appViewClass    = AppView,
        auto_reload     = True,
        static_dir      = "static",
        template_dir    = "templates",
        main_html       = "window.html",
        shared_secret   = None,
        single_instance = False, #
    )
    gui.start(show_frontend=True, block=True)
