from __future__ import annotations
import typing
import jinja2
import weakref
import traceback
import re
import os
import sys
import inspect
import json
import queue
import importlib
import gevent
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyhtmlgui.pyhtmlgui import PyHtmlGui
    from pyhtmlgui.view.pyhtmlview import PyHtmlView
from .lib import WeakFunctionReferences


class PyHtmlGuiInstance:
    def __init__(self, parent: PyHtmlGui):
        self._parent = parent
        self._websocket_connections = []
        self._children = weakref.WeakSet()
        self._template_env = jinja2.Environment(loader=parent.template_loader)
        self._template_cache = {}
        self._call_number = 0
        self._function_references = WeakFunctionReferences()
        self._template_env.globals['_create_py_function_reference'] = self._create_function_reference
        self._view = self._parent.view_class(parent.app_instance, self)

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
                child.set_visible(False)
        if visible is True:
            self.update()

    def call_javascript(self, js_function_name: str, args: list, skip_results: bool = False):
        """
        Call javascript function in frontend.
        :param js_function_name: Name of javascript function
        :param args: Arguments for js function
        :param skip_results: Don't receive results, give some slight performance improvement if we don't wait for result
        """
        self._call_number += 1
        to_delete = self._call_number - 100
        # clean old function references, this is needed to results don't stay around if you don't
        for websocket_connection in self._websocket_connections:
            if to_delete in websocket_connection.javascript_call_result_objects:
                del websocket_connection.javascript_call_result_objects[to_delete]
            if to_delete in websocket_connection.javascript_call_result_queues:
                del websocket_connection.javascript_call_result_queues[to_delete]

        javascript_call_object = {'call': self._call_number, 'name': js_function_name, 'args': args}

        if skip_results is True:
            javascript_call_result = None
            javascript_call_object["skip_results"] = True
        else:
            javascript_call_result = JavascriptCallResult(self._call_number)

        data = json.dumps(javascript_call_object, default=lambda o: None)
        for websocket_connection in self._websocket_connections:
            if skip_results is False:
                websocket_connection.javascript_call_result_objects[self._call_number] = javascript_call_result
                javascript_call_result.add_call(websocket_connection)
            websocket_connection.ws.send(data)
        return javascript_call_result

    def websocket_loop(self, websocket_connection) -> None:
        self._websocket_connections.append(websocket_connection)
        while True:
            msg = websocket_connection.ws.receive()
            if msg is not None:
                message = json.loads(msg)
                gevent.spawn(self._websocket_process_message, message, websocket_connection).run()
            else:
                break
        self._websocket_connections.remove(websocket_connection)
        if len(self._websocket_connections) == 0:
            self.set_visible(False)

    def _websocket_process_message(self, message, websocket_connection):
        if 'call' in message:
            function_name = "Function not found"
            args = "  "
            try:
                if message['name'] == "call_python_function_with_args":
                    functioncall_id = message['args'][0]
                    args = message['args'][1]
                    function = self._function_references.get(functioncall_id)
                    # noinspection PyUnresolvedReferences
                    function_name = "%s.%s" % (function.__self__.__class__.__name__, function.__name__)
                    return_val = function(*args)

                elif message['name'] == "call_python_function":
                    functioncall_id = message['args'][0]
                    function = self._function_references.get(functioncall_id)
                    # noinspection PyUnresolvedReferences
                    function_name = "%s.%s" % (function.__self__.__class__.__name__, function.__name__)
                    return_val = function()

                elif message['name'] == "python_bridge":
                    function_name = "%s.python_bridge" % self.__class__.__name__
                    return_val = None
                    if hasattr(self._view, "on_electron_message"):
                        self._view.on_electron_message(message)

                elif message['name'] == "frontend_ready":
                    function_name = "%s.frontend_ready" % self.__class__.__name__
                    self.update()
                    return_val = None
                    if hasattr(self._view, "on_frontend_ready"):
                        self._view.on_frontend_ready(len(self._websocket_connections))

                else:
                    return_val = None
                    print("unknown python function", message['name'])

            except Exception:
                tb = traceback.format_exc()
                msg = " Exception in: %s(%s)\n" % (function_name, ("%s" % args)[1:-1])
                msg += " %s" % tb.replace("\n", "\n  ").strip()
                self.call_javascript("pyhtmlgui.debug_msg", [msg])
                print(msg)
                return_val = None

            if not ("skip_results" in message and message["skip_results"] is True):
                data = json.dumps({'return': message['call'], 'value': return_val}, default=lambda o: None)
                websocket_connection.ws.send(data)

        elif 'return' in message:
            call_id = message['return']
            del message['return']  # remove internal id from result before passing to next level
            if call_id in websocket_connection.javascript_call_result_objects:
                js_call_result = websocket_connection.javascript_call_result_objects[call_id]
                js_call_result.result_received(websocket_connection, message)
        else:
            print('Invalid message received: ', message)

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
            self._parent.add_file_to_monitor(file_to_monitor, item.__class__.__name__)

        #  replace onclick="pyview.my_function(arg1,arg2)"
        #  with    onclick="pyhtmlgui.call({{_create_py_function_reference(pyview.my_function)}}, arg1, arg2)
        # this a a convinience function is user does not have to type the annoying stuff and functions look cleaner
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
        parts = template.split("{%")
        for i in range(1, len(parts)):
            parts[i] = "{%%%s" % parts[i]

        new_parts = []
        for part in parts:
            if not part.startswith("{%"):
                new_parts.append(part)
            else:
                parts1 = part.split("%}")
                if len(parts1) > 1:
                    parts1[0] = "%s%%}" % parts1[0]
                for p in parts1:
                    new_parts.append(p)

        parts = new_parts
        new_parts = []
        for part in parts:
            parts1 = part.split("{{")
            for i in range(1, len(parts1)):
                parts1[i] = "{{%s" % parts1[i]
            for p in parts1:
                new_parts.append(p)

        parts = new_parts
        new_parts = []
        for part in parts:
            if not part.startswith("{{"):
                new_parts.append(part)
            else:
                parts1 = part.split("}}")
                if len(parts1) > 1:
                    parts1[0] = "%s}}" % parts1[0]
                for p in parts1:
                    new_parts.append(p)

        parts = new_parts
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


class JavascriptCallResult:
    def __init__(self, call_id):
        self.call_id = call_id
        self.websocket_connections = weakref.WeakSet()
        self._results_missing = 0
        self._callback = None

    def add_call(self, websocket_connection):
        websocket_connection.javascript_call_result_queues[self.call_id] = queue.Queue()
        self.websocket_connections.add(websocket_connection)
        self._results_missing += 1

    def result_received(self, websocket_connection, result):
        websocket_connection.javascript_call_result_queues[self.call_id].put(result)
        self._results_missing -= 1
        if self._results_missing == 0 and self._callback is not None:
            self._callback(self._collect_results())

    def _collect_results(self):
        results = []
        for websocket_connection in self.websocket_connections:
            results.append(websocket_connection.javascript_call_result_queues[self.call_id].get())
            del websocket_connection.javascript_call_result_queues[self.call_id]
            del websocket_connection.javascript_call_result_objects[self.call_id]
        errors = [result["error"] for result in results if "error" in result]
        if len(errors) > 0:
            msg = "%s of %s connected frontends returned an error\n" % (len(errors), len(results))
            msg += "\n".join(errors)
            raise Exception(msg)
        return [result["value"] for result in results]

    def __call__(self, callback: typing.Union[typing.Callable, None]  = None):
        if callback is None:
            return self._collect_results()
        else:
            if self._results_missing == 0:
                callback(self._collect_results())
            else:
                self._callback = callback
