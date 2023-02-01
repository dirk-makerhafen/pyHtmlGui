import json, sys
import traceback

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *
from pyhtmlgui import Observable

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)  # enable highdpi scaling
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)  # use highdpi icons

if sys.platform == "darwin":
    import AppKit
    NSApplicationActivationPolicyRegular = 0
    NSApplicationActivationPolicyAccessory = 1
    NSApplicationActivationPolicyProhibited = 2

class PyHtmlQtApp(QApplication):
    def __init__(self, icon_path= None ):
        super(PyHtmlQtApp, self).__init__([])
        self.setQuitOnLastWindowClosed(False)
        self.icon_path = icon_path
        self.icon = QIcon(self.icon_path)
        self.setWindowIcon(self.icon)
        self.on_activated_event = Observable()

    def run(self):
        self.exec_()

    def stop(self, *args):
        self.quit()

    def event(self, e):
        if e.type() == QEvent.ApplicationActivate:
            self.on_activated_event.notify_observers()
        return QApplication.event(self, e)

    def hide_osx_dock(self, *args):
        AppKit.NSApp.setActivationPolicy_(NSApplicationActivationPolicyProhibited)

    def show_osx_dock(self, *args):
        AppKit.NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        self.setWindowIcon(self.icon)


class GenericTray():
    def __init__(self, pyHtmlQtApp, icon_path):
        self.pyHtmlQtApp = pyHtmlQtApp
        self.icon_path = icon_path
        self.icon = QIcon(self.icon_path)
        self.tray = QSystemTrayIcon(self.pyHtmlQtApp)
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)
        self.menu = QMenu()
        self.menu._subitems = {}
        self.tray.setContextMenu(self.menu)
        self.on_left_clicked = Observable()
        self.on_right_clicked = Observable()
        self.tray.activated.connect(self._right_or_left_click)

    def show(self):
        self.tray.show()

    def hide(self):
        self.tray.hide()

    def close(self):
        self.tray.hide()

    def _right_or_left_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.on_left_clicked.notify_observers()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            self.on_right_clicked.notify_observers()


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
        parent = self.menu
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
    def __init__(self, pyHtmlQtApp, url, size, icon_path):
        super().__init__(pyHtmlQtApp, icon_path)
        self.webWidget = PyHtmlWebWidget(url, size=size)
        self.webWidget.load_page()
        self.trayAction = QWidgetAction(self.tray)
        self.trayAction.setDefaultWidget(self.webWidget)
        self.menu.addAction(self.trayAction)

    def addJavascriptFunction(self, name, target):
        self.webWidget.addJavascriptFunction(name, target)

    def removeJavascriptFunction(self, name):
        self.webWidget.removeJavascriptFunction(name)

    def runJavascript(self, javascript, callback=None):
        self.webWidget.runJavascript(javascript, callback)


class PyHtmlQtWindow():
    def __init__(self, pyHtmlQtApp, url, size, title, icon_path=None, keep_connected_on_close = False, keep_connected_on_minimize = True):
        self.pyHtmlQtApp = pyHtmlQtApp
        self.url = url
        self.size = size
        self.title = title
        self.icon_path = icon_path

        self.on_closed_event = Observable()
        self.on_show_event = Observable()
        self.on_minimized_event = Observable()

        self._webWidget = PyHtmlWebWidget(url)
        self._qMainWindow = ExtendedQMainWindow(self) # you could also let this class directly subclass QMainWindow, but then PyHtmlQtWindow will expose a s*load of confusing qt functions from QMainWindow
        self._qMainWindow.resize(size[0], size[1])
        self._qMainWindow.setFocusPolicy(Qt.StrongFocus)
        self._qMainWindow.setWindowTitle(self.title)
        self._qMainWindow.setCentralWidget(self._webWidget)
        self._webWidget.setParent(self._qMainWindow)
        self._menuBar = QMenuBar()
        self._menuBar._subitems = {} # qt also keep track of this, but this is easier for the addMenuButton and addMenuSeparator functions
        self._qMainWindow.setMenuBar(self._menuBar)

        if keep_connected_on_close is False:
            self.on_closed_event.attach_observer(self._webWidget.unload_page)
        if keep_connected_on_minimize is False:
            self.on_minimized_event.attach_observer(self._webWidget.unload_page)
        self.on_show_event.attach_observer(self._webWidget.load_page)

    def show(self, *args):
        self._qMainWindow.showNormal()
        self._qMainWindow.activateWindow()
        self._qMainWindow.raise_()

    def hide(self, *args):
        self._qMainWindow.hide()

    def minimize(self, *args):
        self._qMainWindow.showMinimized()

    def close(self, *args):
        self._qMainWindow.close()

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
    def __init__(self, url, size=None):
        super().__init__()
        self.url  = url
        self._current_url = None
        self.size = size

        self.web = QWebEngineView(parent=self)
        if self.size is not None:
            self.web.setFixedSize(size[0], size[1])

        self.profile = QWebEngineProfile(parent= self) # create a seperate profile for earch webengine, otherwise QWebEngineViews will load only the first loaded url in all view.
        self.web.setPage(QWebEnginePage(self.profile, self.web))
        self.web.load(QUrl("about:blanc"))

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

    def load_page(self, *args):
        if self._current_url != self.url:
            self._current_url = self.url
            self.web.load(QUrl(self.url))

    def unload_page(self, *args):
        if self._current_url != None:
            self._current_url = None
            self.web.load(QUrl("about:blanc"))

    def addJavascriptFunction(self, name, target):
        self._functionHandler.add(name, target)

    def removeJavascriptFunction(self, name):
        self._functionHandler.remove(name)

    def runJavascript(self, javascript, callback=None):
        if callback is None:
            self.web.page().runJavaScript(javascript)
        else:
            self.web.page().runJavaScript(javascript, callback)


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