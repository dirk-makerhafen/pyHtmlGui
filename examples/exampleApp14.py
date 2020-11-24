import time
import threading
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class PageCounter(Observable):
    def __init__(self):
        super().__init__()
        self.count = 0
        self.worker_thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.worker_thread.start()

    def _worker_thread(self):
        while True:
            time.sleep(1)
            self.count += 1
            self.notifyObservers()

class PageView(PyHtmlView):
    TEMPLATE_STR = '''
        Page: {{ this.pagename}}, View Event Count: {{ this.event_count }}, ObservedObject count: {{this.observedObject.count }} <br>
    '''
    def __init__(self, observedObject, parentView, pagename):
        self.pagename = pagename
        self.event_count = 0
        self._on_observedObject_updated = None # detach default event, this is just an example, you could more simply overwrite this method like in the comment below, and ship the whole _on_observedObject_updated_with_count part
        super().__init__(observedObject, parentView)
        self.events.add(observedObject, self._on_observedObject_updated_with_count )# attach our own event listener via self.events. these event are automatically attached and detached based on component visibility

    def _on_observedObject_updated_with_count(self, *kwargs):
        self.event_count += 1
        self.update()

    #def _on_observedObject_updated(self, *kwargs):
    #    self.event_count += 1
    #    self.update()

class App(Observable):
    def __init__(self):
        super().__init__()
        self.counter1 = PageCounter()
        self.counter2 = PageCounter()

class AppView(PyHtmlView):
    TEMPLATE_STR = '''       
        I show gui update event handling, note that the page event counter for the non visible page is not updated while the page is not shown.<br>
        This happens because views that are not visible automatically detach their events from the observed object<br>
        <button onclick="pyhtmlgui.call(this.show_page1)">show page 1</button>
        <button onclick="pyhtmlgui.call(this.show_page2)">show page 2</button>
        <br>
        {{ this.current_page.render() }}
    '''

    def __init__(self, observedObject, parentView):
        super().__init__(observedObject, parentView)
        self.page1 = PageView(observedObject.counter1, self, "Page 1")
        self.page2 = PageView(observedObject.counter2, self, "Page 2")
        self.current_page = self.page1

    def show_page1(self):
        self.set_current_page(self.page1)

    def show_page2(self):
        self.set_current_page(self.page2)

    def set_current_page(self, new_page):
        if new_page != self.current_page:
            self.current_page = new_page
            self.update()

if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance  = App(),
        appViewClass = AppView,
    )
    gui.start(show_frontend=True, block=True)
