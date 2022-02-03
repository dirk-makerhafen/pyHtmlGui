import time
import random
import threading
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class Item(Observable):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.max_position = 500
        self.position = random.randint(0, self.max_position)
        self.direction = -1 if random.random() > 0.5 else 1

    def update(self):
        self.position += self.direction
        if self.position > self.max_position: self.direction = -1
        if self.position < 1: self.direction =  1
        self.notifyObservers()

class SomeAppClassExample(Observable):
    def __init__(self):
        super().__init__()
        self.last_updated = 0
        self.worker_thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.worker_thread.start()

    def _worker_thread(self):
        while True:
            time.sleep(5)
            self.last_updated = time.time()
            self.notifyObservers()

class App(Observable):
    def __init__(self):
        super().__init__()
        self.my_item = SomeAppClassExample()
        self.items = [
            Item("Item_1"),
            Item("Item_2")
        ]
        self.worker_thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.worker_thread.start()

    def _worker_thread(self):
        while True:
            time.sleep(0.01)
            for item in self.items:
                item.update()
            self.notifyObservers() # in this example, this is useless for show only, its only to show that we can ignore this later in the view via self._on_observedObject_updated = None

class ItemView(PyHtmlView):
    TEMPLATE_STR = '''
        <div name="target" style="position:absolute;left:{{this.observedObject.position}}px"> {{ this.observedObject.name}} </div>
    '''
    # this is called if self.observedObject calls notifyObservers(), if you don't overwrite this, it will call update() to rerender the frontend element
    # the event that calls this is detached and attached if the component is visible
    # if you dont want the view updated if the observedObject changes, set _on_observedObject_updated = None in __init__ before call to super
    def _on_observedObject_updated(self, *kwargs):
        self.eval_javascript(
            '''document.getElementById(args.uid).querySelector('[name="target"').style.left = args.position;''',
            skip_results=True, uid = self.uid, position = "%spx" % self.observedObject.position)()  # skip_result for speedup, prevents return data to be send via ws

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        i am a div what is updated by calling javascript via observing the observedObject and overwriting its views _on_observedObject_updated function<br>
        Last rendered: {{ this.last_rendered_timestamp() }}, this should update every 5 seconds because this view observes some object via a manually added event mapping<br>
        Last Trigger call: {{ this.observedObject.my_item.last_updated }} <br>
        {% for item in this.items %}
            {{item.render()}}
        {% endfor %}
    '''
    def __init__(self, observedObject, parentView):
        self._on_observedObject_updated = None # to prevent this view from being automatically updated if observedObject changes
        super().__init__(observedObject, parentView)
        self.events.add(observedObject.my_item, self._on_myitem_updated ) # observe  observedObject.my_item and call our _on_update event. use self.event, so event get automaticall attached and reattached if the object is visible/invisible
        self.items = [ItemView(item, self) for item in observedObject.items ] # if you want this mapping automatically so its updated when observedObject.items changes, see example7 and 8 and use ObservableListView

    def _on_myitem_updated(self, *kwargs):
        self.update()

    def last_rendered_timestamp(self):
        return time.time()

if __name__ == "__main__":
    gui = PyHtmlGui(
        app_instance= App(),
        view_class= AppView,
    )
    gui.start(show_frontend=True, block=True)
