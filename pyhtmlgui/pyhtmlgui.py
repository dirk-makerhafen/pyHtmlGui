import json
import logging
import os
import queue
import shutil
import sys
import threading
import time
import traceback
import uuid
import bottle
import bottle_websocket
import jinja2
import typing
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.logging import create_logger
from .lib import Browser
from .pyhtmlguiInstance import PyHtmlGuiInstance
from .view import PyHtmlView


class PyHtmlGui:
    def __init__(self,
                 app_instance     : object,
                 view_class       : typing.Type[PyHtmlView],
                 static_dir       : str             = "",
                 template_dir     : str             = "",
                 electron_app_dir : str             = None,
                 base_template    : str             = "pyHtmlGuiBase.html",
                 on_view_connected: typing.Callable = None,
                 on_view_disconnected: typing.Callable = None,
                 size             : tuple[int, int] = None,
                 position         : tuple[int, int] = None,
                 browser          : str             = "default",
                 executable       : str             = None,
                 listen_host      : str             = "127.0.0.1",
                 listen_port      : int             = 8000,
                 shared_secret    : str             = None,
                 auto_reload      : bool            = False,
                 single_instance  : bool            = True
                 ) -> None:
        """
        :param app_instance: Some object (eg. main program class instance), passed to view_class as obj on launch
        :param view_class: A class that Inherits from PyHtmlView
        :param static_dir: Static files, css, img go here
        :param template_dir: main.html and other html goes here
        :param electron_app_dir: in case we use electron, this is the electron.js file we launch,
                                 default file is in pyHtmlGui/assets/electron/main.py
        :param base_template: pyHtmlGuiBase in pyHtmlGui/assets/templates, or custom file in app templates dir
        :param size: window size
        :param on_view_connected: callback is called when a frontend connects via websocket,
                                        arguments passed: "nr of view instances", "nr of websocket connections"
        :param on_view_disconnected: callback is called when a frontend websocket is disconnected
                                        arguments passed: "nr of view instances", "nr of websocket connections"
        :param position: window position
        :param browser: default | chrome | electron
        :param executable: path to chrome/electron executable, if needed
        :param listen_host:
        :param listen_port:
        :param shared_secret: use "" to automatically generate a uid internally, None to disable token
        :param auto_reload: for development, monitor files and reload while app is running
        :param single_instance: create only one instance and share it between all connected websockets.
                                This is the default, so one instance of view_class is shared by all connected frontends
        """

        self.view_class = view_class
        self.app_instance = app_instance
        self.static_dir = os.path.abspath(static_dir)
        self.template_dir = os.path.abspath(template_dir)
        self.base_template = base_template
        self.size = size
        self.on_view_connected_callback = on_view_connected
        self.on_view_disconnected_callback = on_view_disconnected
        self.position = position
        self.browser = browser
        self.executable = executable
        self.electron_app_dir = electron_app_dir
        if shared_secret == "":
            self.shared_secret = "%s" % uuid.uuid4()
        elif shared_secret is None:
            self.shared_secret = None
        else:
            self.shared_secret = shared_secret
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.auto_reload = auto_reload
        self.single_instance = single_instance

        if getattr(sys, 'frozen', False) is True:  # check if we are bundled by pyinstaller
            # noinspection PyUnresolvedReferences,PyProtectedMember
            lib_dir = os.path.join(sys._MEIPASS, "pyhtmlgui")
            self.auto_reload = False
        else:
            lib_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)))

        self._template_dir = os.path.join(lib_dir, "assets", "templates")
        self._electron_dir = os.path.join(lib_dir, "assets", "electron")
        if self.electron_app_dir is None:  # use default internal app
            self.electron_app_dir = self._electron_dir
        else:
            if getattr(sys, 'frozen', False) is not True:
                # if we are not frozen, copy our internal lib to the electron target dir if it does not exist
                for f in ["pyhtmlgui.js", "main.js", "package.json"]:
                    lib_js_target = os.path.join(self.electron_app_dir, f)
                    lib_js_source = os.path.join(self._electron_dir, f)
                    if not os.path.exists(lib_js_target):
                        shutil.copyfile(lib_js_source, lib_js_target)

        if not os.path.exists(self.template_dir):
            raise Exception("Template dir '%s' not found" % self.template_dir)
        if not os.path.exists(self.static_dir):
            raise Exception("Static dir '%s' not found" % self.static_dir)

        self.template_loader = jinja2.FileSystemLoader(searchpath=[self._template_dir, self.template_dir])
        self._template_env = jinja2.Environment(loader=self.template_loader, autoescape=jinja2.select_autoescape())

        self._gui_instances = []

        self._token_cookie = "%s" % uuid.uuid4()
        self._token_csrf = "%s" % uuid.uuid4()

        bottle.route("/")(self._main_html)
        bottle.route("/static/<path:path>")(self._static)
        bottle.route("/ws", apply=[bottle_websocket.websocket])(self._websocket)
        self._browser = None
        self._server = WebsocketServer(host=self.listen_host, port=self.listen_port)

        self._file_monitoring = {}
        if self.auto_reload is True:
            t = threading.Thread(target=self._monitoring_thread, daemon=True)
            t.start()

    def start(self, show_frontend: bool = False, block: bool = True) -> None:
        if show_frontend is True:
            self.show()
        self._server.start(block)

    def stop(self) -> None:
        # noinspection PyBroadException
        try:
            self._server.stop()
        except Exception:
            pass

    def show(self) -> None:
        env = None
        target_host = "127.0.0.1" if self.listen_host == "0.0.0.0" else self.listen_host

        if self.browser == "electron":
            args = [self.electron_app_dir, ]
            env = os.environ.copy()
            env.update({
                "PYHTMLGUI_HOST": target_host,
                "PYHTMLGUI_PORT": "%s" % self.listen_port,
                "PYHTMLGUI_SECRET": self.shared_secret,
            })
        else:
            args = ["%s:%s" % (target_host, self.listen_port), ]
            if self.shared_secret is not None:
                args[0] = "%s?token=%s" % (args[0], self.shared_secret)
        if self._browser is None:
            self._browser = Browser(self.browser, self.executable)
        self._browser.open(args, env=env)

    # /main.html
    def _main_html(self):
        if self.shared_secret is not None and bottle.request.query.token != self.shared_secret:
            return bottle.HTTPResponse(status=403)
        template = self._template_env.get_template(self.base_template)
        response = bottle.HTTPResponse(template.render({
            "csrf_token": self._token_csrf,
            "start_size": json.dumps(self.size),
            "start_position": json.dumps(self.position),
        }))
        response.set_header('Cache-Control', 'no-store')
        response.set_header('Set-Cookie', 'token=%s' % self._token_cookie)
        return response

    # /static/<path>
    def _static(self, path: str):
        if bottle.request.get_cookie("token") != self._token_cookie:
            return bottle.HTTPResponse(status=403)
        response = bottle.static_file(path, root=self.static_dir)
        if path.endswith(".js"):
            response.set_header("Content-Type", "application/javascript")
        elif path.endswith(".html"):
            response.set_header("Content-Type", "text/html")
        elif path.endswith(".css"):
            response.set_header("Content-Type", "text/css")
        elif path.endswith(".jpg") or path.endswith(".jpeg"):
            response.set_header("Content-Type", "image/jpeg")
        elif path.endswith(".png"):
            response.set_header("Content-Type", "image/png")
        elif path.endswith(".gif"):
            response.set_header("Content-Type", "image/gif")
        elif path.endswith(".webp"):
            response.set_header("Content-Type", "image/webp")
        elif path.endswith(".svg"):
            response.set_header("Content-Type", "image/svg")

        response.set_header("Cache-Control", "public, max-age=36000")
        return response

    # /ws
    def _websocket(self, ws):
        if bottle.request.get_cookie("token") != self._token_cookie:
            return bottle.HTTPResponse(status=403)
        if bottle.request.query.token != self._token_csrf:
            return bottle.HTTPResponse(status=403)
        websocket_connection = WebsocketConnection(ws)

        if self.single_instance is True:
            if len(self._gui_instances) == 0:
                self._gui_instances.append(PyHtmlGuiInstance(self))
            instance = self._gui_instances[0]
        else:
            instance = PyHtmlGuiInstance(self)
            self._gui_instances.append(instance)

        if self.on_view_connected_callback is not None:
            connections = sum([i.connections_count for i in self._gui_instances]) + 1
            # +1 because connection gets only added in loop later
            self.on_view_connected_callback(len(self._gui_instances), connections)

        instance.websocket_loop(websocket_connection)  # loop while connected

        if instance.connections_count == 0:
            self._gui_instances.remove(instance)
        if hasattr(instance._view, "on_frontend_disconnected"):
            instance._view.on_frontend_disconnected(len(instance._websocket_connections))
        if self.on_view_disconnected_callback is not None:
            connections = sum([i.connections_count for i in self._gui_instances])
            self.on_view_disconnected_callback(len(self._gui_instances), connections)

    def add_file_to_monitor(self, file_to_monitor, class_name) -> None:
        if self.auto_reload is False:
            return
        if file_to_monitor not in self._file_monitoring:
            last_changed = os.path.getmtime(file_to_monitor)
            self._file_monitoring[file_to_monitor] = {
                "file_to_monitor": file_to_monitor,
                "last_changed": last_changed,
                "class_names": set(),
            }
        self._file_monitoring[file_to_monitor]["class_names"].add(class_name)

    def _monitoring_thread(self) -> None:
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
                    except Exception:
                        print("Failed to Update")
                        print(traceback.format_exc())


class WebsocketServer(bottle.ServerAdapter):
    def __init__(self, **options):
        super().__init__(**options)
        self.server = None
        self._server_thread = None
        self.running = False

    def start(self, blocking: bool):
        if self.running is True:
            raise Exception("Websocket server already started!")
        if blocking:
            self.run(bottle.default_app())
        else:
            self._server_thread = threading.Thread(target=self.run, args=[bottle.default_app()], daemon=True)
            self._server_thread.start()

    def stop(self):
        if self.server is not None:
            self.server.stop()

    def run(self, handler):
        self.running = True
        self.server = pywsgi.WSGIServer((self.host, self.port), handler, handler_class=WebSocketHandler)
        if not self.quiet:
            self.server.logger = create_logger('geventwebsocket.logging')
            self.server.logger.setLevel(logging.INFO)
            self.server.logger.addHandler(logging.StreamHandler())
        self.server.serve_forever()
        self._server_thread = None
        self.running = False


class WebsocketConnection:
    def __init__(self, ws):
        self.ws = ws
        self.javascript_call_result_queues = {}
        self.javascript_call_result_objects = {}
        self.active = True
        self.send_queue =queue.Queue()
        self._send_t = threading.Thread(target=self._send_loop, daemon=True)
        self._send_t.start()

    def loop(self, callback):
        while self.active is True:
            msg = self.ws.receive()
            if msg is None:
                break
            try:
                callback(json.loads(msg), self.ws)
            except:
                continue
        self.active = False
        if self.send_queue is not None:
            self.send_queue.put(None)

    def _send_loop(self):
        while self.active is True:
            message = self.send_queue.get()
            if message is None:
                break
            try:
                self.ws.send(message)
            except:
                pass
        self.active = False
        self.send_queue = None

    def send(self, message):
        if self.send_queue is not None:
            self.send_queue.put(message)
