import os, threading, time
from pyHtmlGui import pyHtmlGui, pyHtmlGuiComponent
from pyHtmlGui.observable.observable import Observable


# Main Program
class Example1_App(Observable):
    def __init__(self):
        super().__init__()
        self.current_timestamp = None
        self.run = True
        self.paused = False
        self.updateThread = threading.Thread(target=self._update_thread)
        self.updateThread.start()

    def _update_thread(self):
        while self.run is True:
            self.current_timestamp = time.time()
            self.notifyObservers()
            time.sleep(1)
            while self.paused is True:
                time.sleep(1)

    def setPause(self, paused):
        self.paused = paused
        self.notifyObservers()

    def exit(self):
        self.run = False


class Example1_Gui(pyHtmlGuiComponent):
    TEMPLATE_FILE = "main_window.html"
    def _on_default_event_updated(self,  *kwargs):
        self.update()
        self.update_frontend_element()

    def pause(self): # an example of a local function in the gui object
        self.observedObject.setPause(True)

    def update_frontend_element(self):
        self.javascript_call('$this.find( ".colored_element" ).css( "background-color", "blue" );')

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    example1_App = Example1_App()

    gui = pyHtmlGui(
        observedObject      = example1_App,
        guiComponentClass   = Example1_Gui,

        static_dir         = "static/",
        template_dir       = "templates/",

        main_html          = "app.html",

    )
    gui.run(startFrontend=True, block=False)


