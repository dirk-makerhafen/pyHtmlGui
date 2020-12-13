import logging
import os, json, sys
import threading
import jinja2
import bottle
import bottle_websocket
import uuid
import time
import shutil
import traceback
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.logging import create_logger

from .lib import Browser
from .pyhtmlgui_instance import PyHtmlGuiInstance

class PyHtmlGui():
    def __init__(self,
                 appInstance,               # Some object (eg. main program class instance), passed to appViewClass as obj on launch
                 appViewClass,              # A class that Inherits from PyHtmlView
                 static_dir = "",           # static files, css, img go here
                 template_dir = "",         # main.html and other html goes here
                 electron_app_dir=None,     # in case we use electron, this is the electron.js file we launch, default file is in pyHtmlGui/assets/electron/main.py
                 main_html="pyHtmlGuiBase.html",   # pyHtmlGuiBase in pyHtmlGui/assets/templates, or custom file in app templates dir
                 on_frontend_ready=None,    # If gui connects call this
                 on_frontend_exit = None,   # If gui disconnects call this
                 size = (800, 600),         # window size
                 position = None,           # window position
                 mode = "chrome",           # chrome | electron
                 executable = None,         # path to chrome/electron executable, if needed
                 listen_host = "127.0.0.1",
                 listen_port = 8000,
                 shared_secret="",  # use "" to automatically generate a uid internally, use None to disable token
                 auto_reload = False,       # for development, monitor files and reload while app is running
                 single_instance = True    # create only one instance and share it between all connected websockets, this is the default, so there is only one instance of appViewClass shared by all connected frntends
         ):
        self.appViewClass = appViewClass
        self.appInstance = appInstance
        self.static_dir = os.path.abspath(static_dir)
        self.template_dir = os.path.abspath(template_dir)
        self.on_frontend_ready_callback = on_frontend_ready
        self.on_frontend_exit_callback = on_frontend_exit
        self.main_html = main_html
        self.size = size
        self.position = position
        self.mode = mode
        self.executable = executable
        self.electron_app_dir = electron_app_dir
        if shared_secret == "":
            self.shared_secret = "%s" % uuid.uuid4()
        elif shared_secret == None:
            self.shared_secret = None
        else:
            self.shared_secret = shared_secret
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.auto_reload = auto_reload
        self.single_instance = single_instance

        if getattr(sys, 'frozen', False) == True:  # check if we are bundled by pyinstaller
            lib_dir = os.path.join(sys._MEIPASS, "pyhtmlgui")
            self.auto_reload = False
        else:
            lib_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)))

        self.pyHtmlGui_template_dir =  os.path.join(lib_dir, "assets", "templates")
        self.pyHtmlGui_electron_dir =  os.path.join(lib_dir, "assets", "electron")
        if self.electron_app_dir is None: # use deault internal app
            self.electron_app_dir = self.pyHtmlGui_electron_dir
        else:
            if getattr(sys, 'frozen', False) != True:  # if we are not frozen, copy our internal lib to the electron target dir if it does not exist
                for f in ["pyhtmlgui.js", "main.js"]:
                    lib_js_target = os.path.join(self.electron_app_dir, f)
                    lib_js_source = os.path.join(self.pyHtmlGui_electron_dir, f)
                    if not os.path.exists(lib_js_target):
                        shutil.copyfile(lib_js_source, lib_js_target)

        if not os.path.exists(self.template_dir):
            raise Exception("Template dir '%s' not found" % self.template_dir)
        if not os.path.exists(self.static_dir):
            raise Exception("Static dir '%s' not found" % self.static_dir)

        self._templateLoader = jinja2.FileSystemLoader(searchpath=[self.pyHtmlGui_template_dir, self.template_dir])
        self._templateEnv = jinja2.Environment(loader=self._templateLoader)

        self._gui_instances = []

        self._token_cookie = "%s" % uuid.uuid4()
        self._token_csrf   = "%s" % uuid.uuid4()

        bottle.route("/")(self._main_html)
        bottle.route("/static/<path:path>")(self._static)
        bottle.route("/ws", apply=[bottle_websocket.websocket])(self._websocket)
        self._browser = None
        self._server = MyWebSocketServer(host=self.listen_host, port=self.listen_port)

        self._file_monitoring = {}
        if self.auto_reload is True:
            t = threading.Thread(target=self._monitoring_thread, daemon=True)
            t.start()


    def start(self, show_frontend = False, block=True):
        if show_frontend is True:
            self.show()

        if block is True:
            self._server.run(bottle.default_app())
        else:
            t = threading.Thread(target=self._server.run, args=[bottle.default_app()], daemon=True)
            t.start()

    def stop(self):
        try:
            self._server.server.stop()
        except:
            pass

    def show(self):
        env = None
        if self.mode == "electron":
            args = [ self.electron_app_dir, ]
            env = os.environ.copy()
            env.update({
                "PYHTMLGUI_HOST" : self.listen_host,
                "PYHTMLGUI_PORT" : "%s" % self.listen_port,
                "PYHTMLGUI_SECRET" : self.shared_secret,
            })
        else:
            args = ["%s:%s" % (self.listen_host, self.listen_port),]
            if self.shared_secret is not None:
                args[0] = "%s?token=%s" % (args[0], self.shared_secret)
        if self._browser is None:
            self._browser = Browser(self.mode, self.executable)
        self._browser.open(args, env = env)

    # /main.html
    def _main_html(self):
        if self.shared_secret is not None and bottle.request.query.token != self.shared_secret:
            return bottle.HTTPResponse(status=403)
        template = self._templateEnv.get_template(self.main_html)
        response = bottle.HTTPResponse(template.render({
            "csrf_token"    : self._token_csrf,
            "start_size"    : json.dumps(self.size),
            "start_position": json.dumps(self.position),
        }))
        response.set_header('Cache-Control', 'no-store')
        response.set_header('Set-Cookie', 'token=%s' % self._token_cookie)
        return response

    # /static/<path>/<path>
    def _static(self, path):
        if bottle.request.get_cookie("token") != self._token_cookie:
            return bottle.HTTPResponse(status=403)
        response = bottle.static_file(path, root=self.static_dir)
        response.set_header("Cache-Control", "public, max-age=36000")
        return response

    # /ws
    def _websocket(self, ws):
        if bottle.request.headers.get("Origin") != "http://%s:%s" % (self.listen_host, self.listen_port):
            return bottle.HTTPResponse(status=403)
        if bottle.request.get_cookie("token") != self._token_cookie:
            return bottle.HTTPResponse(status=403)
        if bottle.request.query.token != self._token_csrf:
            return bottle.HTTPResponse(status=403)

        websocketInstance = WebsocketInstance(ws)
        instance = self._get_gui_instance()
        instance.websocket_loop(websocketInstance) # loop while connected
        self._release_gui_instance(instance)

    def _on_frontend_ready(self, pyHtmlGuiInstance): # called by pyHtmlGuiInstance on frontend ready
        if self.on_frontend_ready_callback is not None:
            nr_of_active_frontends = sum([len(instance._websocketInstances) for instance in self._gui_instances])
            self.on_frontend_ready_callback(pyHtmlGuiInstance, nr_of_active_frontends)

    def _get_gui_instance(self):
        if self.single_instance is True:
            if len(self._gui_instances) == 0:
                self._gui_instances.append(PyHtmlGuiInstance(self))
            instance = self._gui_instances[0]
        else:
            instance = PyHtmlGuiInstance(self)
            self._gui_instances.append(instance)
        return instance

    def _release_gui_instance(self, instance):
        if len(instance._websocketInstances) == 0:
            self._gui_instances.remove(instance)

        if self.on_frontend_exit_callback is not None:
            self.on_frontend_exit_callback(instance, sum([len(instance._websocketInstances) for instance in self._gui_instances]))

    def _add_file_to_monitor(self, file_to_monitor, class_name):
        if self.auto_reload is False:
            return
        if file_to_monitor not in self._file_monitoring:
            last_changed = os.path.getmtime(file_to_monitor)
            self._file_monitoring[file_to_monitor] = {
                "file_to_monitor" : file_to_monitor,
                "last_changed"    : last_changed,
                "class_names" : set(),
            }
        self._file_monitoring[file_to_monitor]["class_names"].add(class_name)

    def _monitoring_thread(self):
        while self.auto_reload is True:
            time.sleep(5)
            has_changed = False
            classed_to_reload = []
            for file_to_monitor in self._file_monitoring:
                data = self._file_monitoring[file_to_monitor]
                current_ts = os.path.getmtime(data["file_to_monitor"])
                if current_ts != data["last_changed"]:
                    self._file_monitoring[file_to_monitor]["last_changed"] = current_ts
                    classed_to_reload.extend(self._file_monitoring[file_to_monitor]["class_names"])
                    has_changed = True
            if has_changed is True:
                for instance in self._gui_instances:
                    instance.clear_template_cache(classed_to_reload)
                    try:
                        instance.update()
                    except Exception as e:
                        print("Failed to Update")
                        print(traceback.format_exc())

class MyWebSocketServer(bottle.ServerAdapter):
    def run(self, handler):
        self.server = pywsgi.WSGIServer((self.host, self.port), handler, handler_class=WebSocketHandler)
        if not self.quiet:
            self.server.logger = create_logger('geventwebsocket.logging')
            self.server.logger.setLevel(logging.INFO)
            self.server.logger.addHandler(logging.StreamHandler())
        self.server.serve_forever()

class WebsocketInstance():
    def __init__(self, ws):
        self.ws = ws
        self.javascript_call_result_queues = {}
        self.javascript_call_result_objects = {}
