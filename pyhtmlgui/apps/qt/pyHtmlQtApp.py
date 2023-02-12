import json, sys
import traceback
import logging
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *
from pyhtmlgui import Observable
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)  # enable highdpi scaling
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)  # use highdpi icons

AppKit = None
if sys.platform == "darwin":
    try:
        import AppKit
    except:
        logging.warning("AppKit not available, hiding dock icon will not be available. Run 'pip install pyobjc' to install ")
    NSApplicationActivationPolicyRegular = 0
    NSApplicationActivationPolicyAccessory = 1
    NSApplicationActivationPolicyProhibited = 2



ERROR_PAGE = '''
 <div style="text-align:center;color:gray">
    <h3>
        <br>
        failed to load app window
        <br>
        :(  
        <br>
        retrying in a few seconds
    </h3>
</div>
'''

class PyHtmlQtApp(QApplication):
    def __init__(self, icon_path= None ):
        super(PyHtmlQtApp, self).__init__([])
        self.setQuitOnLastWindowClosed(False)
        self._icon_cache = {}
        self._current_icon = None
        self.set_icon(icon_path)
        self.on_about_to_quit_event = Observable()
        self.on_activated_event = Observable()
        self.aboutToQuit.connect(self.on_about_to_quit_event.notify_observers)

    def run(self):
        self.exec_()

    def stop(self):
        self.on_about_to_quit_event.notify_observers() # notify here, because tray does not hide after app quit, so we need to notify them
        self.quit()

    def set_icon(self, path):
        if path not in self._icon_cache:
            self._icon_cache[path] = QIcon(path)
        self._current_icon = self._icon_cache[path]
        self.setWindowIcon(self._icon_cache[path])

    def event(self, e):
        if e.type() == QEvent.ApplicationActivate and e.spontaneous() is True:
            self.on_activated_event.notify_observers()
        return QApplication.event(self, e)

    def hide_osx_dock(self):
        if AppKit is not None:
            AppKit.NSApp.setActivationPolicy_(NSApplicationActivationPolicyProhibited)
        else:
            logging.warning("AppKit not available, hide_osx_dock() is not available")

    def show_osx_dock(self):
        if AppKit is not None:
            AppKit.NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            self.setWindowIcon(self._current_icon)
        else:
            logging.warning("AppKit not available, show_osx_dock() is not available")


class GenericTray():
    def __init__(self, pyHtmlQtApp, icon_path):
        self._pyHtmlQtApp = pyHtmlQtApp
        self._tray = QSystemTrayIcon(self._pyHtmlQtApp)
        self._icon_cache = {}
        self.set_icon(icon_path)
        self._tray.setVisible(True)

        self._menu = QMenu()
        self._menu._subitems = {}

        self._tray.setContextMenu(self._menu)

        self.on_left_clicked = Observable()
        self.on_right_clicked = Observable()
        self.on_closed_event = Observable()
        self.on_show_event = Observable()

        self.menu_is_open = False
        self._tray.activated.connect(self._right_or_left_click)
        self._menu.aboutToHide.connect(self.on_closed_event.notify_observers) # https://doc.qt.io/qt-5/macos-issues.html#menu-actions
        self._menu.aboutToShow.connect(self.on_show_event.notify_observers)
        self.on_show_event.attach_observer(self._menu_shown)
        self.on_closed_event.attach_observer(self._menu_hidden)

    def show(self):
        self._tray.show()

    def hide(self):
        self._tray.hide()

    def close(self):
        self._tray.hide()

    def set_icon(self, path):
        if path not in self._icon_cache:
            self._icon_cache[path] = QIcon(path)
        self._tray.setIcon(self._icon_cache[path])

    def _right_or_left_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.on_left_clicked.notify_observers()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            self.on_right_clicked.notify_observers()

    def _menu_shown(self):
        self.menu_is_open = True

    def _menu_hidden(self):
        self.menu_is_open = False


class PyHtmlQtSimpleTray(GenericTray):

    def addAction(self, name_or_names, target):
        if type(name_or_names) == str:
            name_or_names = [ name_or_names]
        submenu = self._get_submenu(name_or_names[:-1])
        action = QAction(parent=submenu, text=name_or_names[-1])
        action.triggered.connect(target)
        submenu.addAction(action)

    def addSeparator(self, names = []):
        submenu = self._get_submenu(names)
        submenu.addSeparator()

    def _get_submenu(self, names):
        parent = self._menu
        for name in names:
            if name in parent._subitems:
                parent = parent._subitems[name]
            else:
                subitem = parent.addMenu(name)
                subitem._subitems = {}
                parent._subitems[name] = subitem
                parent = subitem
        return parent


class PyHtmlQtTray(GenericTray):
    def __init__(self, pyHtmlQtApp, url, size, icon_path, keep_connected_on_close = True, error_page=""):
        super().__init__(pyHtmlQtApp, icon_path)
        pyHtmlQtApp.on_about_to_quit_event.attach_observer(self.close)

        self._webWidget = PyHtmlWebWidget(url, size=size, error_page= error_page)
        self._trayAction = QWidgetAction(self._tray)
        self._trayAction.setDefaultWidget(self._webWidget)
        self._menu.addAction(self._trayAction)
        if keep_connected_on_close is False:
            self.on_show_event.attach_observer(self._webWidget.load_page)
            self.on_closed_event.attach_observer(self._webWidget.unload_page)
        else:
            self._webWidget.load_page() # load page now if it should stay active in background

    def hide(self):
        if self.menu_is_open is True:
            self._trayAction.trigger()  # on osx, if tray is in focus app will not exit, so trigger trayAction to hide it.
        super(PyHtmlQtTray, self).hide()

    def close(self):
        if self.menu_is_open is True:
            self._trayAction.trigger()  # on osx, if tray is in focus app will not exit, so trigger trayAction to hide it.
        super(PyHtmlQtTray, self).close()

    def addJavascriptFunction(self, name, target):
        self._webWidget.addJavascriptFunction(name, target)

    def removeJavascriptFunction(self, name):
        self._webWidget.removeJavascriptFunction(name)

    def runJavascript(self, javascript, callback=None):
        self._webWidget.runJavascript(javascript, callback)


class PyHtmlQtWindow():
    def __init__(self, pyHtmlQtApp, url, size, title, icon_path=None, keep_connected_on_close = False, keep_connected_on_minimize = True, error_page=""):
        self._pyHtmlQtApp = pyHtmlQtApp
        pyHtmlQtApp.on_about_to_quit_event.attach_observer(self.close)

        self.on_closed_event = Observable()
        self.on_show_event = Observable()
        self.on_minimized_event = Observable()

        self._webWidget = PyHtmlWebWidget(url, error_page=error_page)
        self._qMainWindow = ExtendedQMainWindow(self) # you could also let this class directly subclass QMainWindow, but then PyHtmlQtWindow will expose a s*load of confusing qt functions from QMainWindow
        self._qMainWindow.resize(size[0], size[1])
        self._qMainWindow.setFocusPolicy(Qt.StrongFocus)
        self._qMainWindow.setWindowTitle(title)
        self._qMainWindow.setCentralWidget(self._webWidget)
        self._webWidget.setParent(self._qMainWindow)
        self._menuBar = QMenuBar()
        self._menuBar._subitems = {} # qt also keep track of this, but this is easier for the addMenuButton and addMenuSeparator functions
        self._qMainWindow.setMenuBar(self._menuBar)

        self._icon_cache = {}
        self.set_icon(icon_path)

        if keep_connected_on_close is False:
            self.on_closed_event.attach_observer(self._webWidget.unload_page)
        if keep_connected_on_minimize is False:
            self.on_minimized_event.attach_observer(self._webWidget.unload_page)
        self.on_show_event.attach_observer(self._webWidget.load_page)

    def show(self):
        self._qMainWindow.showNormal()
        self._qMainWindow.activateWindow()
        self._qMainWindow.raise_()

    def hide(self):
        self._qMainWindow.hide()

    def minimize(self):
        self._qMainWindow.showMinimized()

    def close(self):
        self._qMainWindow.close()

    def set_title(self, title):
        self._qMainWindow.setWindowTitle(title)

    def set_icon(self, path):
        if path not in self._icon_cache:
            self._icon_cache[path] = QIcon(path)
        self._qMainWindow.setWindowIcon(self._icon_cache[path])

    def addMenuButton(self, name_or_names, target):
        if type(name_or_names) == str:
            name_or_names = [ name_or_names]
        submenu = self._get_submenu(name_or_names[:-1])
        action = QAction(text=name_or_names[-1], parent=submenu)
        action.triggered.connect(target)
        submenu.addAction(action)

    def addMenuSeparator(self, names = []):
        submenu = self._get_submenu(names)
        submenu.addSeparator()

    def addJavascriptFunction(self, name, target):
        self._webWidget.addJavascriptFunction(name, target)

    def removeJavascriptFunction(self, name):
        self._webWidget.removeJavascriptFunction(name)

    def runJavascript(self, javascript, callback=None):
        self._webWidget.runJavascript(javascript, callback)

    def _get_submenu(self, names):
        parent = self._menuBar
        for name in names:
            if name in parent._subitems:
                parent = parent._subitems[name]
            else:
                subitem = parent.addMenu(name)
                subitem._subitems = {}
                parent._subitems[name] = subitem
                parent = subitem
        return parent


class PyHtmlWebWidget(QWidget):
    def __init__(self, url, size=None, error_page = ""):
        super().__init__()
        self.url  = url
        self._current_url = None
        self._page_loaded = False
        self._error_page = error_page
        if self._error_page == "":
            self._error_page = ERROR_PAGE

        self.web = QWebEngineView(parent=self)
        if size is not None:
            self.web.setFixedSize(size[0], size[1])

        self.profile = QWebEngineProfile(parent= self) # create a seperate profile for earch webengine, otherwise QWebEngineViews will load only the first loaded url in all view.
        self.web.setPage(QWebEnginePage(self.profile, self.web))
        self.web.loadFinished.connect(self._on_page_loaded)
        self.web.load(QUrl("about:blank"))

        self.channel = QWebChannel(parent=self.web)
        self._functionHandler = JavascriptFunctionHandler()
        self.channel.registerObject('pyhtmlapp', self._functionHandler)
        self.web.page().setWebChannel(self.channel)

        self.layout = QGridLayout()
        self.layout.addWidget(self.web, 0, 0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.setRowStretch(0, 0)
        self.setLayout(self.layout)

        self._page_reload_timer = QTimer()
        self._page_reload_timer.timeout.connect(self.load_page)

    def load_page(self):
        self._page_reload_timer.stop()
        if self._current_url != self.url:
            self._current_url = self.url
            self._page_loaded = False
            self.web.load(QUrl(self.url))

    def unload_page(self):
        if self._current_url != None:
            self._current_url = None
            self._page_loaded = False
            self.web.load(QUrl("about:blank"))

    def addJavascriptFunction(self, name, target):
        self._functionHandler.add(name, target)

    def removeJavascriptFunction(self, name):
        self._functionHandler.remove(name)

    def runJavascript(self, javascript, callback=None):
        if callback is None:
            self.web.page().runJavaScript(javascript)
        else:
            self.web.page().runJavaScript(javascript, callback)

    def _on_page_loaded(self, success):
        if self._current_url is not None:
            if success is True:
                self.web.page().toHtml(self._after_page_loaded)
            else:
                self._page_loaded = False
                self._on_pageload_failed()

    def _after_page_loaded(self, html):
        self._page_loaded = "pyhtmlgui" in html
        if self._page_loaded is False:
            self._on_pageload_failed()

    def _on_pageload_failed(self):
        self._page_reload_timer.stop()
        if self._current_url is not None:
            self._current_url = None
            if self._error_page is not None:
                self.web.page().setHtml(self._error_page)
            self._page_reload_timer.start(3000)

class ExtendedQMainWindow(QMainWindow):
    def __init__(self, pyHtmlQtWindow):
        self.pyHtmlQtWindow = pyHtmlQtWindow
        super().__init__()

    def closeEvent(self, event) -> None:
        self.pyHtmlQtWindow.on_closed_event.notify_observers()

    def showEvent(self, event) -> None:
        self.pyHtmlQtWindow.on_show_event.notify_observers()

    def hideEvent(self, event) -> None:
        self.pyHtmlQtWindow.on_minimized_event.notify_observers()


class JavascriptFunctionHandler(QObject):
    def __init__(self):
        super().__init__()
        self._actions = {}

    @pyqtSlot(str, str, result=str)
    def call(self, action_name, arguments):
        if action_name not in self._actions:
            return json.dumps({"exception": "Unknown function pyhtmlapp.%s, did you forget to call addJavascriptFunction ?" % action_name})
        try:
            arguments = json.loads(arguments) # do in multiple lines, so if something failes, we see where.
            action = self._actions[action_name]
            result = action(*arguments)
            return json.dumps({"result" : result})
        except Exception as e:
            msg = "Exception while calling python from javascript function 'pyhtmlapp.%s'\n%s" %  (action_name, traceback.format_exc())
            return json.dumps({"exception": msg })

    def add(self, name, target):
        self._actions[name] = target

    def remove(self, name):
        self._actions.pop(name)

    def get(self, name):
        return  self._actions[name]