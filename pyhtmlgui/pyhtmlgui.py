from __future__ import annotations

import json
import os
import logging
import sys
import threading
import time
import traceback
import uuid
import webbrowser

import jinja2
import typing
from werkzeug.serving import make_server

from .pyhtmlguiInstance import PyHtmlGuiInstance
from .view import PyHtmlView
import flask, flask_sock


class PyHtmlGui:
    def __init__(self,
                 app_instance     : object,
                 view_class       : typing.Type[PyHtmlView],
                 static_dir       : str             = None,
                 template_dir     : str             = None,
                 base_template    : str             = "pyHtmlGuiBase.html",
                 on_view_connected: typing.Callable = None,
                 on_view_disconnected: typing.Callable = None,
                 size             : tuple[int, int] = None,
                 position         : tuple[int, int] = None,
                 listen_host      : str             = "127.0.0.1",
                 listen_port      : int             = 8000,
                 shared_secret    : str             = None,
                 auto_reload      : bool            = False,
                 single_instance  : bool            = True
                 ) -> None:
        """
        :param app_instance: Some object (eg. main program class instance), passed to view_class as obj on launch
        :type  app_instance: object
        :param view_class: A class that Inherits from PyHtmlView
        :param static_dir: Static files, css, img go here
        :param template_dir: main.html and other html goes here
        :param base_template: pyHtmlGuiBase in pyHtmlGui/assets/templates, or custom file in app templates dir
        :param size: window size
        :param on_view_connected: callback is called when a frontend connects via websocket,
                                        arguments passed: "nr of view instances", "nr of websocket connections"
        :param on_view_disconnected: callback is called when a frontend websocket is disconnected
                                        arguments passed: "nr of view instances", "nr of websocket connections"
        :param position: window position
        :param listen_host:
        :param listen_port:
        :param shared_secret: use "" to automatically generate a uid internally, None to disable token
        :param auto_reload: for development, monitor files and reload while app is running
        :param single_instance: create only one instance and share it between all connected websockets.
                                This is the default, so one instance of view_class is shared by all connected frontends
        """

        self._endpoints = {}

        self.add_endpoint(
            name          = "",
            app_instance  = app_instance,
            view_class    = view_class,
            base_template = base_template,
            on_view_connected   = on_view_connected,
            on_view_disconnected= on_view_disconnected,
            single_instance     = single_instance,
            size     = size,
            position = position,
        )

        if shared_secret == "":
            self.shared_secret = "%s" % uuid.uuid4()
        elif shared_secret is None:
            self.shared_secret = None
        else:
            self.shared_secret = shared_secret

        self.listen_host = listen_host
        self.listen_port = listen_port
        self.auto_reload = auto_reload

        self.static_dir = None if static_dir is None else os.path.abspath(static_dir)
        self.template_dir = None if template_dir is None else os.path.abspath(template_dir)

        if getattr(sys, 'frozen', False) is True:
            # noinspection PyUnresolvedReferences,PyProtectedMember
            self._internal_template_dir = os.path.join(sys._MEIPASS, "pyhtmlgui", "assets", "templates")
            self.auto_reload = False
        else:
            self._internal_template_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "templates")
        if self.template_dir is not None and not os.path.exists(self.template_dir):
            raise Exception("Template dir '%s' not found" % self.template_dir)
        if self.static_dir is not None and not os.path.exists(self.static_dir):
            raise Exception("Static dir '%s' not found" % self.static_dir)

        self.template_loader = jinja2.FileSystemLoader(searchpath=[self._internal_template_dir] if self.template_dir is None else [self._internal_template_dir, self.template_dir])
        self._template_env = jinja2.Environment(loader=self.template_loader, autoescape=jinja2.select_autoescape())

        self._token_cookie = "%s" % uuid.uuid4()
        self._token_csrf = "%s" % uuid.uuid4()

        self.flaskApp = flask.Flask("pyhtmlgui", static_folder=None, template_folder=None)

        self.flaskWebsocket =  flask_sock.Sock()
        self.flaskApp.route("/")(self._main_html)
        self.flaskApp.route("/<endpoint>")(self._main_html)
        if self.static_dir is not None:
            self.flaskApp.route("/static/<path:path>")(self._static)
        self.flaskWebsocket.route("/ws")(self._websocket)
        self.flaskWebsocket.init_app(self.flaskApp)

        self._server = WebsocketServerThread(self.flaskApp, self.listen_host, self.listen_port)

        self._file_monitoring = {}
        if self.auto_reload is True:
            t = threading.Thread(target=self._monitoring_thread, daemon=True)
            t.start()

    def start(self, show_frontend: bool = False, block: bool = True) -> None:
        self._server.start()
        if show_frontend is True:
            self.show()
        if block is True:
            self.join()

    def stop(self) -> None:
        # noinspection PyBroadException
        try:
            self._server.shutdown()
        except Exception:
            pass

    def join(self):
        self._server.join()

    def show(self) -> None:
        for endpoint in self._endpoints.values():
            endpoint.show()

    def add_endpoint(self, app_instance: object, view_class: typing.Type[PyHtmlView], name: str = "", base_template: str = "pyHtmlGuiBase.html",
         on_view_connected: typing.Callable = None, on_view_disconnected: typing.Callable = None,
         single_instance: bool = True, size: tuple[int, int] = None, position: tuple[int, int] = None ):
        if name in self._endpoints:
            raise Exception("Endpoint named '%s' already exists" % name)
        self._endpoints[name] = PyHtmlGuiEndpoint(
            parent        = self,
            app_instance  = app_instance,
            name          = name,
            view_class    = view_class,
            base_template = base_template,
            on_view_connected    = on_view_connected,
            on_view_disconnected = on_view_disconnected,
            single_instance      = single_instance,
            size     = size,
            position = position
        )

    def get_url(self, endpoint = ""):
        if endpoint in self._endpoints:
            return self._endpoints[endpoint].get_url()
        return None

    # /
    def _main_html(self, endpoint = ""):
        if self.shared_secret is not None and flask.request.args.get('token') != self.shared_secret:
            return flask.abort(403)
        if endpoint not in self._endpoints:
            return flask.abort(404)
        template = self._template_env.get_template(self._endpoints[endpoint].base_template)
        response = flask.Response(template.render({
            "csrf_token"    : self._token_csrf,
            "start_size"    : json.dumps(self._endpoints[endpoint].size),
            "start_position": json.dumps(self._endpoints[endpoint].position),
        }))
        response.headers['Cache-Control'] = 'no-store'
        response.set_cookie("token", self._token_cookie)
        response.set_cookie("endpoint", endpoint)
        return response

    # /static/<path>
    def _static(self, path: str):
        if flask.request.cookies.get('token') != self._token_cookie:
            return flask.abort(403)
        if self.static_dir is None:
            return flask.abort(404)
        response = flask.helpers.send_from_directory( self.static_dir, path, max_age=36000)

        if path.endswith(".js"):
            response.headers["Content-Type"] =  "application/javascript"
        elif path.endswith(".html"):
            response.headers["Content-Type"] =  "text/html"
        elif path.endswith(".css"):
            response.headers["Content-Type"] =  "text/css"
        elif path.endswith(".jpg") or path.endswith(".jpeg"):
            response.headers["Content-Type"] =  "image/jpeg"
        elif path.endswith(".png"):
            response.headers["Content-Type"] =  "image/png"
        elif path.endswith(".gif"):
            response.headers["Content-Type"] =  "image/gif"
        elif path.endswith(".webp"):
            response.headers["Content-Type"] =  "image/webp"
        elif path.endswith(".svg"):
            response.headers["Content-Type"] =  "image/svg"

        response.headers["Cache-Control"] = "public, max-age=36000"
        return response

    # /ws
    def _websocket(self, ws, endpoint= ""):
        endpoint = flask.request.cookies.get('endpoint',"")
        if flask.request.cookies.get('token') != self._token_cookie or flask.request.args.get('token') != self._token_csrf:
            msg = "token_failed"
        elif endpoint not in self._endpoints:
            msg = "no_endpoint"
        else:
            self._endpoints[endpoint].process_websocket(ws)
            msg = None
        try:
            ws.close(message=msg)
        except:
            pass

    def _add_file_to_monitor(self, file_to_monitor, class_name) -> None:
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
                for endpoint in self._endpoints:
                    for instance in self._endpoints[endpoint]._gui_instances:
                        instance.clear_template_cache(classed_to_reload)
                        try:
                            instance.update()
                        except Exception:
                            logging.error("Failed to update, %s" % traceback.format_exc())


class WebsocketServerThread(threading.Thread):
    def __init__(self, app, host, port ):
        threading.Thread.__init__(self, daemon=True)
        self.server = make_server(host, port, app, threaded=True)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class PyHtmlGuiEndpoint:
    def __init__(self, parent: PyHtmlGui, app_instance: object, view_class: typing.Type[PyHtmlView], name: str = "",
         base_template    : str             = "pyHtmlGuiBase.html",
         on_view_connected: typing.Callable = None, on_view_disconnected: typing.Callable = None,
         single_instance : bool = True, size: tuple[int, int] = None, position: tuple[int, int] = None,
    ) -> None:
        self.parent = parent
        self.view_class = view_class
        self.app_instance = app_instance
        self.base_template = base_template
        self.size = size
        self.on_view_connected_callback = on_view_connected
        self.on_view_disconnected_callback = on_view_disconnected
        self.position = position
        self.single_instance = single_instance
        self.name = name
        self._gui_instances = []

    def process_websocket(self, ws):
        if len(self._gui_instances) == 0 or self.single_instance is False:
            instance = PyHtmlGuiInstance(self.parent, self.app_instance, self.view_class)
            self._gui_instances.append(instance)
        else:
            instance = self._gui_instances[0]

        if self.on_view_connected_callback is not None:
            self.on_view_connected_callback(len(self._gui_instances), sum([i.connections_count for i in self._gui_instances]) + 1) # +1 because connection gets only added in loop later

        instance.process(ws)  # loop while connected

        # release/remove Instance
        if instance.connections_count == 0:
            self._gui_instances.remove(instance)
        if hasattr(instance._view, "on_frontend_disconnected"):
            instance._view.on_frontend_disconnected(len(instance._websocket_connections))
        if self.on_view_disconnected_callback is not None:
            self.on_view_disconnected_callback(len(self._gui_instances), sum([i.connections_count for i in self._gui_instances]))

    def get_url(self):
        target_host = "127.0.0.1" if self.parent.listen_host == "0.0.0.0" else self.parent.listen_host
        url = "http://%s:%s/%s" % (target_host, self.parent.listen_port, self.name)
        if self.parent.shared_secret is not None:
            url = "%s?token=%s" % (url, self.parent.shared_secret)
        return url

    def show(self) -> None:
        webbrowser.open(self.get_url(), 1)
