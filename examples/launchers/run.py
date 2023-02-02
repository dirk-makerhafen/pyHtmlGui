import time, threading, sys, os
import webbrowser
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable
from pyhtmlgui.apps import PyHtmlChromeApp
from pyhtmlgui.apps.qt import PyHtmlQtApp, PyHtmlQtWindow, PyHtmlQtTray, PyHtmlQtSimpleTray

class CounterApp(Observable):
    def __init__(self):
        super().__init__()
        self.value = 0
        self.active = True
        self.worker_thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.worker_thread.start()
        self.on_app_exited = Observable()

    def _worker_thread(self):
        while self.active is True:
            self.set_value(self.value + 1)
            time.sleep(1)
        self.on_app_exited.notify_observers()

    def set_value(self, value):
        self.value = value
        self.notify_observers()

    def exit(self):
        if self.active != False:
            self.active = False
            self.notify_observers()

    def join(self): # wait for exit
        self.worker_thread.join()

class TrayView(PyHtmlView):
    TEMPLATE_STR = '''
        <div style="text-align:center">
            {% if pyview.subject.active %}
                <h3>Hi from Tray</h3>
                <button onclick="pyhtmlapp.show_app()" >Show App</button> <br>
                <button onclick="pyhtmlapp.hide_app()" >Hide App</button> <br>
                <button onclick="pyhtmlapp.minimize_app()" >Minimize App</button> <br>
                <button onclick="pyview.subject.exit()">Exit App</button> <br>
            {% else %}
                <p>App exiting</p>
                <script>
                    pyhtmlapp.hide_app();
                    // This is not needed, as the qt app will listen for on_app_exited of our app logic and exit accordingly.
                    // It will make the frontend disappear faster if its not waiting for the app logic to exit. 
                    // This may be needed if your app logic and pyhtmlgui service run as a background progress or on another host
                    // and you want your app logic to communicate to the qt part of you app
                </script>
            {% endif %}
        </div>
    '''

class CounterAppView(PyHtmlView):
    TEMPLATE_STR = '''
        <div style="text-align:center">
            {% if pyview.subject.active %}
                <h4>Current value: {{ pyview.subject.value }}</h4>
                <button onclick='pyview.subject.set_value(0);'> Reset Counter </button> <br><br>
            {% else %}
                <p>App exiting</p>
            {% endif %}
            <script>
                function osx_preferences_clicked(){
                    alert("This is a example for OSX menu button overwrites, and for calling javascript from the QT part of your app. Its not a good idea to call alert(), as this will halt the event loop")
                }
            </script>
        </div>
    '''

if __name__ == "__main__":
    modes = ["service", "default_browser", "default_browser_with_simple_tray", "chrome_app","chrome_app_with_simple_tray", "native_app", "native_app_with_simple_tray","native_app_with_html_tray", ]
    mode = sys.argv[-1]
    if mode not in modes:
        print("Available modes: \n  %s" % ("\n  ".join(modes)))
        print("Use 'python run.py <mode>' to select mode")
        exit(0)

    script_dir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    app_icon_path = os.path.join(script_dir, "icons/app.ico")   # on osx, app_icon will be the dock icon and window icon has no effect.
    tray_icon_path = os.path.join(script_dir, "icons/tray.ico") # otherwise, different windows can have different icons
    window_icon_path = os.path.join(script_dir, "icons/window.ico")

    applogic =  CounterApp()

    guiservice = PyHtmlGui(
        app_instance = applogic,
        view_class   = CounterAppView,
        listen_port=8001,
    )

    if mode == "service": # start no gui, only run service
        print("Starting gui at %s" % guiservice.get_url())
        guiservice.start()

    elif mode == "default_browser": # open in local default browser tab
        print("Starting gui at %s, opening in default browser" % guiservice.get_url())
        guiservice.start(show_frontend=True)

    elif mode == "default_browser_with_simple_tray": # open in local default browser tab
        print("Starting gui at %s, opening as tray app" % guiservice.get_url())
        guiservice.start(block=False)
        qt_app = PyHtmlQtApp()
        if sys.platform == "darwin": # normally all apps have a dock icon, but we only want to be shows in tray
            qt_app.hide_osx_dock()
        tray = PyHtmlQtSimpleTray(qt_app, icon_path=tray_icon_path)
        tray.addAction("Show", lambda x: webbrowser.open(guiservice.get_url(), 1))
        tray.addAction("Exit", applogic.exit)
        applogic.on_app_exited.attach_observer(qt_app.stop) # stop qt frontend app if app logic has exited
        qt_app.run() # is blocking

    elif mode == "chrome_app": # show with chrome browser in app mode
        print("Starting gui at %s, opening as chrome app" % guiservice.get_url())
        guiservice.start(block=False)
        chrome = PyHtmlChromeApp(url=guiservice.get_url())
        applogic.on_app_exited.attach_observer(chrome.close)
        chrome.show()
        chrome.join() # wait for chrome to exit
        applogic.exit() # in case chrome gets closed and our applogics exit function did not get called

    elif mode == "chrome_app_with_simple_tray":
        print("Starting gui at %s, opening as chrome app with simple tray" % guiservice.get_url())
        guiservice.start(block=False)
        chrome = PyHtmlChromeApp(url=guiservice.get_url())
        qt_app = PyHtmlQtApp(icon_path=app_icon_path)
        tray = PyHtmlQtSimpleTray(qt_app, icon_path=tray_icon_path)
        tray.addAction("Show", chrome.show)
        tray.addAction("Hide", chrome.close)
        tray.addSeparator()
        tray.addAction("Exit", applogic.exit)

        applogic.on_app_exited.attach_observer(qt_app.stop) # stop qt frontend app if app logic has exited

        chrome.show()
        qt_app.run()
        chrome.close()

    elif mode == "native_app": # show as native app main window using QT
        guiservice.start(block=False)
        qt_app = PyHtmlQtApp(icon_path=app_icon_path)
        window = PyHtmlQtWindow(qt_app, guiservice.get_url(), [600, 300], "My App Window Name", icon_path=window_icon_path)

        if sys.platform == "darwin":         # on OSX, overwrite the default menu bar.
            window.addMenuButton(["File", "Exit"], applogic.exit)  # this will overwrite the default osx menus "quit <application>" button, for other names that have special meaning on osx see https://www.riverbankcomputing.com/static/Docs/PyQt4/qmenubar.html#qmenubar-on-mac-os-x
            window.addMenuButton(["File", "Preferences"], lambda x: window.runJavascript("osx_preferences_clicked()"))  # this will overwrite the default osx menus "Preferences" button
            window.addMenuButton(["View", "Show"], window.show) # because on osx the menu bar always visible you might as well use it
            window.addMenuButton(["View", "Hide"], window.hide)
            qt_app.on_activated_event.attach_observer(window.show)  # on osx, show window again if dock if clicked
            qt_app.on_about_to_quit_event.attach_observer(applogic.exit)  # this will capture the dock icon context menu quit button, that can not be removed on osx and will always close the qt app
        else:
            window.on_closed_event.attach_observer(applogic.exit) # else exit app if window is closed
        applogic.on_app_exited.attach_observer(qt_app.stop) # stop qt frontend app if app logic has exited

        window.show()
        qt_app.run()

    elif mode == "native_app_with_simple_tray": # show as native app main window using QT
        guiservice.start(block=False)
        qt_app = PyHtmlQtApp(icon_path= app_icon_path)
        window = PyHtmlQtWindow(qt_app, guiservice.get_url(), [600, 300], "My App Window Name", icon_path=window_icon_path)

        tray = PyHtmlQtSimpleTray(qt_app, icon_path=tray_icon_path)
        tray.addAction("Show", window.show)
        tray.addAction("Minimize", window.minimize)
        tray.addAction(["Hide","HideMe"], window.close)
        tray.addSeparator()
        tray.addAction("Exit", applogic.exit)

        if sys.platform == "darwin":
            window.addMenuButton(["File", "Exit"], applogic.exit)  # this will overwrite the default osx menus "quit <application>" button, for other names that have special meaning on osx see https://www.riverbankcomputing.com/static/Docs/PyQt4/qmenubar.html#qmenubar-on-mac-os-x
            window.on_closed_event.attach_observer(qt_app.hide_osx_dock) # hide dock item if window is closed, aka "minimize to tray"
            window.on_show_event.attach_observer(qt_app.show_osx_dock)   # show dock icon again
            qt_app.on_activated_event.attach_observer(window.show)       # if dock is click, show window
            qt_app.on_about_to_quit_event.attach_observer(applogic.exit)  # this will capture the dock icon context menu quit button, that can not be removed on osx and will always close the qt app
        else:
            tray.on_left_clicked.attach_observer(window.show) # on windows, left click on tray will open the main window, right click will automatially open the menu
        applogic.on_app_exited.attach_observer(qt_app.stop) # stop qt frontend app if app logic has exited

        window.show()
        qt_app.run()

    elif mode == "native_app_with_html_tray": # show as native app main window using QT
        guiservice.add_endpoint(app_instance=applogic, view_class=TrayView, name="tray")
        guiservice.start(block=False)
        qt_app = PyHtmlQtApp(icon_path=app_icon_path)
        window = PyHtmlQtWindow(qt_app, guiservice.get_url("")  , [ 600, 300], "My App Window Name", icon_path=window_icon_path)
        tray   = PyHtmlQtTray(qt_app, guiservice.get_url("tray"), [ 300, 200], icon_path=tray_icon_path, keep_connected_on_close=False)
        tray.addJavascriptFunction("show_app", window.show) # expose this function as pyhtmlapp.show_app  to trays javascript
        tray.addJavascriptFunction("hide_app", window.close)
        tray.addJavascriptFunction("minimize_app", window.minimize)

        if sys.platform == "darwin":
            window.addMenuButton(["File", "Quit"], applogic.exit)  # this will overwrite the default osx menus "quit <application>" button, for other names that have special meaning on osx see https://www.riverbankcomputing.com/static/Docs/PyQt4/qmenubar.html#qmenubar-on-mac-os-x
            window.on_closed_event.attach_observer(qt_app.hide_osx_dock) # hide dock item if window is closed, aka "minimize to tray"
            window.on_show_event.attach_observer(qt_app.show_osx_dock)# show dock icon again
            qt_app.on_activated_event.attach_observer(window.show) # if dock is click, show window
            qt_app.on_about_to_quit_event.attach_observer(applogic.exit) # this will capture the dock icon context menu quit button, that can not be removed on osx and will always close the qt app
        else:
            tray.on_left_clicked.attach_observer(window.show) # on windows, left click on tray will open the main window, right click will automatially open the menu
        applogic.on_app_exited.attach_observer(qt_app.stop) # stop qt frontend app if app logic has exited

        window.show()
        qt_app.run()

    else:
        print("unknown mode '%s'" % mode)

    # At this point, we either did a clean shutdown, or the app was somehow force quit maybe by a system shutdown,
    # or on osx by the dock icon context menu quit button. so cleanup and exit your app logic if needed here
    applogic.exit()
    applogic.join()
    guiservice.stop() # this is not really needed, we exit anyway.