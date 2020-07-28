import os, random, json, sys
import queue
import threading
import jinja2
import gevent
import bottle
import bottle_websocket
import uuid
import time
import weakref

from .browsers import browsers
from .lib import WeakFunctionReferences

class pyHtmlGui():

    def __init__(self,
                 guiComponentClass,         # A class that Inherits from Component
                 observedObject,            # Some object (eg. main program class instance), passed to guiComponentClass as obj on launch
                 static_dir = "",                # static files and templates go here
                 template_dir = "",              # main.html and other html goes here
                 exit_callback = None,      # If gui disconnects call this
                 main_html = "pyHtmlGuiBase.html",   # pyHtmlGuiBase in pyHtmlGui static dir, or custom file in static_dir
                 size = (800, 600),         # window size
                 position = None,           # window position
                 mode = "chrome",
                 executable = None,
                 electron_main_js = None,
                 shared_secret = None,
         ):

        self.guiComponentClass = guiComponentClass
        self.objInstance = observedObject
        self.static_dir = static_dir
        self.template_dir = template_dir
        self.exit_callback = exit_callback
        self.main_html = main_html
        self.mode = mode
        self.executable = executable
        self.electron_main_js = electron_main_js

        self.function_references = WeakFunctionReferences()
        self._call_return_values = {}
        self._call_return_callbacks = {}
        self._exposed_py_functions = {}  # exposed python functions
        self._exposed_js_functions = []  # exposed javascript functions
        self._call_number = 0
        self._websockets = []

        self.host = "127.0.0.1"
        self.port = 8000
        self._cmdline_args = ['--no-sandbox', '--disable-http-cache']
        if shared_secret is None:
            self.token_launch = "%s" % uuid.uuid4()
        else:
            self.token_launch = shared_secret
        self.token_cookie = "%s" % uuid.uuid4()
        self.token_csrf   = "%s" % uuid.uuid4()
        self.size = size
        self.position = position

        if getattr(sys, 'frozen', False) == True:  # check if we are bundled by pyinstaller
            self.pyHtmlGui_static_dir =  os.path.join(sys._MEIPASS, "pyHtmlGui", "static")
        else:
            self.pyHtmlGui_static_dir =  os.path.join(os.path.dirname(os.path.realpath(__file__)), "static")
        self.pyHtmlGui_js = open(os.path.join(self.pyHtmlGui_static_dir, "pyHtmlGui.js"), "r").read()
        self._pyHtmlGui_js_cache = None

        @self.expose
        def call_python_function_with_args(callback_id, args):
            print("call_python_function_with_args", callback_id)
            self.function_references.get(callback_id)(*args)

        @self.expose
        def call_python_function(callback_id):
            print("call_python_function", callback_id)
            self.function_references.get(callback_id)()

        @self.expose
        def frontend_ready(exposed_js_functions):
            self._exposed_js_functions = exposed_js_functions

        def get_function_callback_id(function):
            if type(function) == jinja2.runtime.Undefined:
                raise Exception("Undefined python method in script: '%s'" % function._undefined_name)
            return self.function_references.add(function)

        templateLoader = jinja2.FileSystemLoader(searchpath=[self.template_dir])
        self._templateEnv = jinja2.Environment(loader=templateLoader)
        templateLoaderStatic = jinja2.FileSystemLoader(searchpath=[self.static_dir, self.pyHtmlGui_static_dir])
        self._templateEnvStatic = jinja2.Environment(loader=templateLoaderStatic)
        self._templateEnv.globals['py'] = get_function_callback_id

        self._event_queue = queue.Queue(500)
        self._children = weakref.WeakSet()

        self.gui_instance = guiComponentClass(self.objInstance, self)

        self._event_thread = threading.Thread(target=self._event_thread_function)
        self._event_thread .daemon = True
        self._event_thread .start()

        bottle.route("/")(self._main_html)
        bottle.route("/pyHtmlGui.js")(self._pyHtmlGui_js)
        bottle.route("/static/<path:path>")(self._static)
        bottle.route("/pyHtmlGui", apply=[bottle_websocket.websocket])(self._websocket)

    def run(self, startFrontend = False, block=True):
        if startFrontend is True:
            self.show()

        def _run():
            return bottle.run(
                host  = self.host,
                port  = self.port,
                server= bottle_websocket.GeventWebSocketServer,
                quiet = False)
        if block is True:
            _run()
        else:
            t = threading.Thread(target=_run)
            t.daemon = True
            t.start()

    def show(self):
        if self.executable is not None:
            browsers.set_path(self.mode, self.executable)

        start_url = "%s:%s?token=%s" % (self.host, self.port, self.token_launch)
        options = {
            "mode"          : self.mode,
            "cmdline_args"  : self._cmdline_args,
        }
        if self.electron_main_js is not None:
            options["main_js"] = os.path.abspath(os.path.join(self.static_dir, self.electron_main_js))
            options["main_js_argv"] = [os.path.abspath(self.static_dir) ]
        browsers.open(start_url, options)

    # Expose decorator makes py function available in js
    def expose(self, name_or_function=None):
        # Deal with '@pyHtmlGui.expose()' - treat as '@pyHtmlGui.expose'
        if name_or_function is None:
            return self.expose

        if type(name_or_function) == str:   # Called as '@peakt.expose("my_name")'
            name = name_or_function
            def decorator(function):
                self._expose(name, function)
                return function
            return decorator
        else:
            function = name_or_function
            self._expose(function.__name__, function)
            return function

    def _expose(self, name, function):
        msg = 'Already exposed function with name "%s"' % name
        assert name not in self._exposed_py_functions, msg
        self._exposed_py_functions[name] = function
        self._pyHtmlGui_js_cache = None


    def _event_thread_function(self):
        while True:
            event_data  = self._event_queue.get()
            if event_data[0] == "render":
                event, target_id, obj_to_render = event_data
                html = obj_to_render._template.render({"this":obj_to_render})
                html = html.replace("$this", '$("#%s")' % obj_to_render.uid)
                print("render",target_id, html)
                self._javascript_call("set_element", [target_id,html])

            elif event_data[0] == "javascript_call":
                event, name, args, result_callback =  event_data
                r = self._javascript_call(name, args)
                if result_callback is not None:
                    r(callback=result_callback)

            else:
                raise Exception("Unkown pyHtmlGui event '%s'" % event_data[0])

    # Call a Javascript function
    def _javascript_call(self, name, args):
        if name not in self._exposed_js_functions:
            raise Exception("Javascript function '%s' is not known to python code, did you epose it?" % name)
        call_object = self._javascript_call_create_callobject(name, args)
        for ws in self._websockets:
            self._websocket_repeated_send(ws, json.dumps(call_object, default=lambda o: None))    #
        return self._javascript_call_create_resultobject(call_object)

    def _javascript_call_create_callobject(self, name, args):
        self._call_number += 1
        call_id = self._call_number + random.random()
        r = {'call': call_id, 'name': name, 'args': args}
        return r

    def _javascript_call_create_resultobject(self, call):
        call_id = call['call']
        def return_func(callback=None):
            if callback is not None:
                self._call_return_callbacks[call_id] = callback
            else:
                for w in range(10000):
                    if call_id in self._call_return_values:
                        return self._call_return_values.pop(call_id)
                    gevent.sleep(0.001)
        return return_func


    # /main.html
    def _main_html(self):
        if bottle.request.query.token != self.token_launch:
            return bottle.HTTPResponse(status=403)
        #self.token_launch = "%s" % uuid.uuid4()

        template = self._templateEnvStatic.get_template(self.main_html)
        response = bottle.HTTPResponse(template.render({
            "gui_instance" : self.gui_instance,
            "csrf_token"   : self.token_csrf,
        }))

        response.set_header('Cache-Control', 'no-store')
        response.set_header('Set-Cookie', 'token=%s' % self.token_cookie)
        return response

    # /pyHtmlGui.js
    def _pyHtmlGui_js(self):
        if bottle.request.get_cookie("token") != self.token_cookie:
            return bottle.HTTPResponse(status=403)

        start_geometry = {
            'default': { 'size': self.size, 'position':self.position },
            'pages': {}
        }
        if self._pyHtmlGui_js_cache is None:
            self._pyHtmlGui_js_cache = self.pyHtmlGui_js.replace('/** _py_functions **/', '_py_functions: %s,' % list(self._exposed_py_functions.keys()))
            self._pyHtmlGui_js_cache = self._pyHtmlGui_js_cache.replace('/** _start_geometry **/', '_start_geometry: %s,' % json.dumps(start_geometry, default=lambda o: None))

        bottle.response.content_type = 'application/javascript'
        bottle.response.set_header('Cache-Control', 'no-store')
        return self._pyHtmlGui_js_cache

    # /static/<path>/<path>
    def _static(self, path):
        if bottle.request.get_cookie("token") != self.token_cookie:
            return bottle.HTTPResponse(status=403)

        response = bottle.static_file(path, root=self.static_dir)
        #response.set_header('Cache-Control', 'no-store')
        response.set_header("Cache-Control", "public, max-age=60")
        return response

    # /pyHtmlGui
    def _websocket(self, ws):
        if bottle.request.headers.get("Origin") != "http://%s:%s" % (self.host, self.port):
            return bottle.HTTPResponse(status=403)
        if bottle.request.get_cookie("token") != self.token_cookie:
            return bottle.HTTPResponse(status=403)
        if bottle.request.query.token != self.token_csrf:
            return bottle.HTTPResponse(status=403)

        self._websockets += [ws,]

        while True:
            msg = ws.receive()
            if msg is not None:
                message = json.loads(msg)
                gevent.spawn(self._websocket_process_message, message, ws).run()
            else:
                self._websockets.remove(ws)
                break

        self._websocket_close()

    def _websocket_close(self):
        if self.exit_callback is not None:
            sockets = [ws for ws in self._websockets]
            self.exit_callback(sockets)

    def _websocket_process_message(self, message, ws):
        if "error" in message:
            raise Exception(message["error"])
        if 'call' in message:
            return_val = self._exposed_py_functions[message['name']](*message['args'])
            self._websocket_repeated_send(ws, json.dumps({ 'return': message['call'], 'value': return_val  }, default=lambda o: None))
        elif 'return' in message:
            call_id = message['return']
            if call_id in self._call_return_callbacks:
                callback = self._call_return_callbacks.pop(call_id)
                callback(message['value'])
            else:
                self._call_return_values[call_id] = message['value']
        else:
            print('Invalid message received: ', message)

    def _websocket_repeated_send(self, ws, msg):
        for attempt in range(100):
            try:
                ws.send(msg)
                break
            except Exception:
                gevent.sleep(0.001)


    def _add_child(self, child):
        self._children.add(child)

    def _remove_child(self, child):
        self._children.remove(child)




