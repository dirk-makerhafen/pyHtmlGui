from __future__ import annotations

import threading
import time
import typing
import jinja2
import weakref
import traceback
import re
import os
import sys
import inspect
import json
import logging
import queue
import importlib
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyhtmlgui.pyhtmlgui import PyHtmlGui
    from pyhtmlgui.view.pyhtmlview import PyHtmlView
from .lib import WeakFunctionReferences

class PyHtmlGuiInstance:
    def __init__(self, parent: PyHtmlGui, app_instance: object, view_class: typing.Type[PyHtmlView], _on_dom_ready_callback):
        self._parent = parent
        self._on_dom_ready_callback = _on_dom_ready_callback
        self._websocket_connections = []
        self._children = weakref.WeakSet()
        self._template_env = jinja2.Environment(loader=parent.template_loader, autoescape=jinja2.select_autoescape())
        self._template_cache = {}
        self._call_number = 0
        self._function_references = WeakFunctionReferences()
        self._template_env.globals['_create_py_function_reference'] = self._create_function_reference
        self.pending_js_results = {}
        self._polling_children = {}
        self._polling_thread = None
        self._view = view_class(app_instance, self)

    @property
    def connections_count(self) -> int:
        return len(self._websocket_connections)

    def update(self) -> None:
        self.call_javascript("pyhtmlgui.update_element", ["pyHtmlGuiBody", self._view.render()], skip_results=True)

    def set_visible(self, visible: bool) -> None:
        """
        Set component and childens visibility, components that are not visible get their events detached
        """
        if visible is False:
            for child in self._children:
                try:
                    if child.is_visible is True:
                        child.set_visible(False)
                except Exception as e:
                    pass
        else:
            self.update()

    def call_javascript(self, js_function_name: str, args: list = None, skip_results: bool = False):
        """
        Call javascript function in frontend.
        :param js_function_name: Name of javascript function
        :param args: Arguments for js function
        :param skip_results: Don't receive results, give some slight performance improvement if we don't wait for result
        """

        self._call_number  += 1
        call_id = self._call_number

        try:  #remove old function references, this may not be needed, because it should be removed on return from python, but in case of error it may stay forever otherwise
            self.pending_js_results[call_id - 1000].removed_by_parent() # will call outstanding callbacks, collecting as many results as have been received at this point
            del self.pending_js_results[call_id - 1000] # no more that 1000 calls should stay around
        except:
            pass

        javascript_call_object = {'call': call_id, 'name': js_function_name, 'args': args if args is not None else []}
        javascript_call_result = None
        if skip_results is False:
            javascript_call_result = JavascriptCallResult(self, call_id, len(self._websocket_connections) )
            self.pending_js_results[call_id] = javascript_call_result
        else:
            javascript_call_object["skip_results"] = True

        data = json.dumps(javascript_call_object, default=lambda o: None)
        for websocket_connection in [w for w in self._websocket_connections]:
            websocket_connection.send(data)
        return javascript_call_result

    def process(self, ws) -> None:
        websocket_connection = WebsocketConnection(ws, self)
        self._websocket_connections.append(websocket_connection)
        websocket_connection.receive_loop()
        self._websocket_connections.remove(websocket_connection)
        if len(self._websocket_connections) == 0:
            self.set_visible(False)

    def _create_function_reference(self, function: typing.Union[typing.Callable, jinja2.runtime.Undefined]) -> str:
        if type(function) == jinja2.runtime.Undefined:
            # noinspection PyProtectedMember
            raise Exception("Undefined python method in script: '%s'" % function._undefined_name)
        return self._function_references.add(function)

    def get_template(self, item: PyHtmlView, force_reload: bool = False):
        """
        Receive template associated to item
        :param item: The view Object
        :param force_reload: Force reloading of template
        :return:
        """
        if force_reload is False:
            try:
                return self._template_cache[item.__class__.__name__]
            except KeyError:
                pass

        if item.__class__.TEMPLATE_FILE is not None:  # load from file
            file_to_monitor = self._template_env.get_template(item.TEMPLATE_FILE).filename
            string_to_render = open(file_to_monitor, "r").read()
        else:  # load from class
            if self._parent.auto_reload is False:
                string_to_render = item.TEMPLATE_STR
                file_to_monitor = None
            else:
                module_name = item.__module__
                if module_name is None or module_name == str.__class__.__module__:
                    module_fullname = item.__class__.__name__  # Avoid reporting __builtin__
                else:
                    module_fullname = module_name + '.' + item.__class__.__name__

                try:
                    file_to_monitor = os.path.abspath(inspect.getfile(item.__class__))
                except Exception:  # in case its in main. this may be a bug in inspect
                    file_to_monitor = os.path.abspath(sys.argv[0])

                if module_name == "__main__":
                    name = os.path.splitext(os.path.basename(file_to_monitor))[0]
                    module = __import__(name)
                    importlib.reload(module)  # reload should work on non complex objects in __main__, but not for more
                    for comp in module_fullname.split(".")[1:]:
                        module = getattr(module, comp)
                else:
                    loader = importlib.machinery.SourceFileLoader(module_name, file_to_monitor)
                    # noinspection PyUnresolvedReferences
                    spec = importlib.util.spec_from_loader(loader.name, loader)
                    # noinspection PyUnresolvedReferences
                    module = importlib.util.module_from_spec(spec)
                    loader.exec_module(module)
                    module = getattr(module, module_fullname.split(".")[-1])
                string_to_render = module.TEMPLATE_STR

        if self._parent.auto_reload is True:
            self._parent._add_file_to_monitor(file_to_monitor, item.__class__.__name__)

        string_to_render = self._prepare_template(string_to_render)

        try:
            self._template_cache[item.__class__.__name__] = self._template_env.from_string(string_to_render)
        except Exception as e:
            msg = "Failed to load Template "
            if item.TEMPLATE_FILE is not None:
                msg += "from File '%s': " % item.TEMPLATE_FILE
            else:
                msg += "from Class '%s': " % item.__class__.__name__
            msg += " %s" % e
            raise Exception(msg)

        return self._template_cache[item.__class__.__name__]

    @staticmethod
    def _prepare_template(template: str) -> str:
        """
            Replace onclick="pyview.my_function(arg1,arg2)"
            with    onclick="pyhtmlgui.call({{_create_py_function_reference(pyview.my_function)}}, arg1, arg2)
        """
        parts = re.split('({{|}}|{%|%})', template)
        index = 0
        while index < len(parts):
            if parts[index] == "{{" or parts[index] == "{%" :
                parts[index] = "%s%s%s" % (parts[index] , parts[index+1], parts[index+2])
                del parts[index+ 1]
                del parts[index+ 1]
            index += 1

        new_parts = []
        for i, part in enumerate(parts):
            if part.startswith("{{") or part.startswith("{%") or part.find("pyview.") == -1:
                new_parts.append(part)
            else:
                # noinspection RegExpSingleCharAlternation
                subparts = re.split(r'(>| |\(|=|\"|\'|\n|\r|\t|;)(pyview.[a-zA-Z0-9_.]+\()', part)
                for x, subpart in enumerate(subparts):
                    if subpart.startswith("pyview."):
                        subpart = subpart.replace("(", ")}}, ", 1)
                        subparts[x] = "pyhtmlgui.call({{_create_py_function_reference(%s" % subpart
                for sp in subparts:
                    new_parts.append(sp)
        return "".join(new_parts).replace(r'\pyview.', 'pyview.')

    def clear_template_cache(self, classnames: str = None) -> None:
        if classnames is None:
            self._template_cache = {}
        else:
            for classname in classnames:
                try:
                    del self._template_cache[classname]
                except Exception:
                    pass

    def _add_child(self, child: PyHtmlView) -> None:
        self._children.add(child)

    def _remove_child(self, child: PyHtmlView) -> None:
        self._children.remove(child)

    def _add_polling_child(self, child: PyHtmlView) -> None:
        if self._polling_thread == None:
            self._polling_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._polling_thread.start()
        try:
            if child in self._polling_children[child._autoupdate_interval]:
                return
        except:
            pass
        self._remove_polling_child(child) # in case interval has changed and child already exists in some queue
        if child._autoupdate_interval not in self._polling_children:
            self._polling_children[child._autoupdate_interval] = weakref.WeakSet()
        self._polling_children[child._autoupdate_interval].add(child)

    def _remove_polling_child(self, child):
        for key in self._polling_children.keys():
            try:
                self._polling_children[key].remove(child)
            except:
                pass
            if len(self._polling_children[key]) == 0:
                del self._polling_children[key]

    def _poll_loop(self):
        i = 0
        while True:
            now = time.time()
            for key in self._polling_children.keys():
                interval = int(key)
                if i % interval == 0:
                    for child in self._polling_children[key]:
                        if child.is_visible and child._last_rendered + interval/2.0 < now:
                            child.update()
            i += 1
            time.sleep(1)


class WebsocketConnection:
    def __init__(self, ws, pyHtmlGuiInstance):
        self.ws = ws
        self.parent_instance = pyHtmlGuiInstance
        self.active = True
        self.send_queue = queue.Queue(maxsize=1000)
        self._send_t = threading.Thread(target=self._send_loop, daemon=True)
        self._send_t.start()

    def receive_loop(self):
        while self.active is True:
            try:
                msg = self.ws.receive()
            except:
                msg = None
            if msg is None:
                break
            try:
                self._process_received_message(json.loads(msg))
            except:
                continue
        try:
            self.ws.close()
        except:
            pass
        self.active = False
        if self.send_queue is not None:
            self.send_queue.put(None)

    def send(self, message):
        if self.send_queue is not None:
            self.send_queue.put(message)

    def _process_received_message(self, message):
        if 'call' in message:
            function_name = "Function not found"
            args = "  "
            return_val = None
            try:
                if message['name'] == "call_python_function_with_args":
                    functioncall_id = message['args'][0]
                    args = message['args'][1]
                    function = self.parent_instance._function_references.get(functioncall_id)
                    # noinspection PyUnresolvedReferences
                    function_name = "%s.%s" % (function.__self__.__class__.__name__, function.__name__)
                    return_val = function(*args)

                elif message['name'] == "call_python_function":
                    functioncall_id = message['args'][0]
                    function = self.parent_instance._function_references.get(functioncall_id)
                    # noinspection PyUnresolvedReferences
                    function_name = "%s.%s" % (function.__self__.__class__.__name__, function.__name__)
                    return_val = function()

                elif message['name'] == "frontend_ready":
                    function_name = "frontend_ready"
                    self.parent_instance.update()
                    self.parent_instance._on_dom_ready_callback()

                elif message['name'] == "ping":
                    pass

                else:
                    logging.error("unknown python function '%s'" % message['name'])

            except Exception:
                tb = traceback.format_exc()
                msg = " Exception in: %s(%s)\n" % (function_name, ("%s" % args)[1:-1])
                msg += " %s" % tb.replace("\n", "\n  ").strip()
                self.parent_instance.call_javascript("pyhtmlgui.debug_msg", [msg], skip_results=True)
                logging.error(msg)
                return_val = None

            if not ("skip_results" in message and message["skip_results"] is True):
                data = json.dumps({'return': message['call'], 'value': return_val}, default=lambda o: None)
                self.send(data)

        elif 'return' in message:
            call_id = message['return']
            del message['return']  # remove internal id from result before passing to next level
            try:
                self.parent_instance.pending_js_results[call_id].result_received(message)
            except:
                pass
        else:
            logging.error('Invalid message received: %s' % message)

    def _send_loop(self):
        while self.active is True:
            message = self.send_queue.get()
            if message is None:
                break
            try:
                self.ws.send(message)
            except:
                pass
        try:
            self.ws.close()
        except:
            pass
        self.active = False
        self.send_queue = None


class JavascriptCallResult:
    def __init__(self, pyHtmlGuiInstance, call_id, nr_of_expected_results):
        self.instance = pyHtmlGuiInstance
        self.call_id = call_id
        self._results_expected = nr_of_expected_results
        self.results = []
        self._callback = None
        self._all_results_received_event = threading.Event()

    def result_received(self, result):
        self.results.append(result)
        if len(self.results) == self._results_expected:
            if self._callback is not None:
                self._callback(self.results)
            self._all_results_received_event.set()
            self._clear_parent_reference()

    def _get_results_blocking(self):
        self._all_results_received_event.wait(60)
        errors = [result["error"] for result in self.results if "error" in result]
        if len(errors) > 0:
            msg = "%s of %s connected frontends returned an error\n" % (len(errors), len(self.results))
            msg += "\n".join(errors)
            raise Exception(msg)
        return [result["value"] for result in self.results]

    def removed_by_parent(self):
        self._all_results_received_event.set()

    def _clear_parent_reference(self):
        try:
            del self.instance.pending_js_results[self.call_id]  # remove pending reference
        except:
            pass

    def __call__(self, callback: typing.Union[typing.Callable, None]  = None):
        if callback is None:
            r = self._get_results_blocking()
            self._clear_parent_reference()
            return r
        else:
            if self._all_results_received_event.is_set() is True:
                callback(self._get_results_blocking())
                self._clear_parent_reference()
            else:
                self._callback = callback
