from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class App(Observable):
    pass

class DummyView(PyHtmlView):
    TEMPLATE_STR = '''Edit me at runtime and save file, the frontend will update after a few seconds when filesystem changes are detected'''

class AppView(PyHtmlView):
    TEMPLATE_FILE = "app.html"

    def __init__(self, observedObject, parentView):
        super().__init__(observedObject, parentView)
        self.dummyview = DummyView(observedObject, self)

    def click_me(self): # this is clicked in html frontend, arrived here, calles create_random_number from app.js, then updated the result in the frontend
        self.call_javascript("create_random_string",["This part was created in python,"])(self.echo_back_to_frontends) # only call with callback of ignore result, don't call with () here, this will block the event loop

    # if you set shared_instance = True below, and open multile windows,
    # you will see feedback values from all open frontends here, else every connected frontend has its own AppView Instance
    def echo_back_to_frontends(self, values):
        #self.eval_javascript('''document.getElementById(args.uid).querySelector('[name="result"').innerHTML = args.innerHTML;''', skip_results=True, uid=self.uid, innerHTML="<br>".join(values))
        self.call_javascript("pyhtmlgui.eval_script", [
            '''document.getElementById(args.uid).querySelector('[name="result"').innerHTML = args.innerHTML;''',
            { "uid": self.uid, "innerHTML": "<br>".join(values) }
        ], skip_results=True)

if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance     = App(),
        appViewClass    = AppView,
        static_dir      = "static",
        template_dir    = "templates",
        main_html       = "window.html",
        auto_reload     = True, # Debug only, if you changed the class template_str or files, the frontend will update views on rumtime. try editing app.html while app is running and waid few seconds
        single_instance = False, # if you set this to False, open multiple windows, see one AppView connected to multiple frontends,
    )
    gui.start(show_frontend=True, block=True)
