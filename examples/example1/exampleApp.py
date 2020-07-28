import os, threading, time
from pyHtmlGui import pyHtmlGui, pyHtmlGuiComponent
from pyHtmlGui.observable.observable import Observable


# Main Program
class Example1_App(Observable):
    def __init__(self):
        super().__init__()
        self.current_timestamp = None
        self.run = True
        self.updateThread = threading.Thread(target=self._update_thread)
        self.updateThread.start()

    def _update_thread(self):
        while self.run is True:
            self.current_timestamp = time.time()
            self.notifyObservers()
            time.sleep(1)

    def stop(self):
        self.run = False


class Example1_Gui(pyHtmlGuiComponent):
    TEMPLATE_STR = '''
        <p style="text-align:center"> {{ this.observedObject.current_timestamp }} </p>
    '''


if __name__ == "__main__":

    example1_App = Example1_App()

    gui = pyHtmlGui(
        observedObject      = example1_App,
        guiComponentClass   = Example1_Gui,
    )
    gui.run(startFrontend=True, block=False)
