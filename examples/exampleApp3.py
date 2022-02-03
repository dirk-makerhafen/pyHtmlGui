import time
import threading
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class App(Observable):
    pass

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        i am a item that is updated by a thread in the python frontend object<br>
        {{ this.value }}<br>
         <button onclick='pyhtmlgui.call(this.pause_restart);'> {% if this.paused == True %} Start {% else %} Pause {% endif %}</button>
    '''
    def __init__(self, observedObject, parentView):
        super().__init__(observedObject, parentView)
        self.value = 0
        self.paused = True
        self.worker_thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.worker_thread.start()

    def _worker_thread(self):
        self.insert_element()
        while True:
            if self.paused is False:
                self.value = time.time()
                if self.is_visible is True: # if we call update ourself, we need to check visibility, we cant update invisible components.
                    self.update()
            time.sleep(1)

    def pause_restart(self):
        self.paused = not self.paused
        if self.is_visible is True: #This is why we normalle observe some other object, so events deals with this. see example4 to see how to do this correctly
            self.update()

if __name__ == "__main__":
    gui = PyHtmlGui(
        app_instance= App(),
        view_class= AppView,
    )
    gui.start(show_frontend=True, block=True)
