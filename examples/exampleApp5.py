import sys
sys.path.insert(0, ".")
import time
import random
import threading
from pyHtmlGui import PyHtmlGui, PyHtmlView, Observable

class App(Observable):
    pass

class ItemView(PyHtmlView):
    TEMPLATE_STR = '''
        <div name="target" style="position:absolute;left:{{this.position}}px"> x </div>
    '''
    def __init__(self, observedObject, parentView):
        super().__init__(observedObject, parentView)
        self.max_position = 500
        self.position = random.randint(0,self.max_position)
        self.direction = -1 if random.random() > 0.5 else 1

    def do_update_via_js(self):
        self.position += self.direction
        if self.position > self.max_position: self.direction = -1
        if self.position < 1: self.direction =  1
        if self.is_visible:
            self.call_javascript("pyhtmlgui.eval_script", [
                '''document.getElementById(args.uid).querySelector('[name="target"').style.left = args.position;''',
                {
                    "uid": self.uid,
                    "position": "%spx" % self.position
                }
            ], skip_results=True) # skip_result for speedup, prevents return data to be send via ws
            # This is equivalent to the shorter, nicer version:
            #self.eval_javascript('''document.getElementById(args.uid).querySelector('[name="target"').style.left = args.position;''',
            #    skip_results=True, uid = self.uid, position = "%spx" % self.position)


class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        i am a div what is updated by calling javascript from the python frontend object<br>
        {% for item in this.subitems %}
            {{item.render()}} <br>
        {% endfor %}
    '''
    def __init__(self, observedObject, parentView):
        super().__init__(observedObject, parentView)
        self.subitems = [
            ItemView(observedObject, self),
            ItemView(observedObject, self),
        ]
        self.worker_thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.worker_thread.start()

    def _worker_thread(self):
        while True:
            time.sleep(0.01)
            for item in self.subitems:
                item.do_update_via_js()

if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance  = App(),
        appViewClass = AppView,
    )
    gui.start(show_frontend=True, block=True)
