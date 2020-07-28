import time
import threading
from pyHtmlGui.observable.observable import Observable

# Some backend process "automatically" (via observable) updating the frontend
class Example1(Observable):
    def __init__(self):
        super().__init__()
        self.current_timestamp = None
        self.run = True
        self.updateThread = threading.Thread(target=self._update_thread)
        self.updateThread.start()

    def _update_thread(self):
        while self.run is True:
            self.current_timestamp = time.time()
            print("currnet ts updated")
            self.notifyObservers()
            time.sleep(1)

    def stop(self):
        self.run = False


# A backend python method called from a frontend button, receiving a frontend  field
class Example2():
    def __init__(self):
        self.add_two_numbers_last_result = None

    def add_two_numbers(self, a, b):
        r = a+b
        self.add_two_numbers_last_result = r
        return r

# Some backend process calling a frontend JS function from time to time
class Example3():
    def __init__(self):
        pass

# The main class of our example app
class BackendAppMain():
    def __init__(self):
        self.some_string = "Hallo"
        self.example1 = Example1()
        self.example2 = Example2()
        self.example3 = Example3()

    def on_gui_exit(self, *args, **kwargs):
        print("exit reveived")
        self.example1.stop()