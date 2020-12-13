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
from .lib import WeakFunctionReferences

class PyHtmlGuiInstance():
    def __init__(self, pyHtmlGui ):
        self._pyHtmlGui = pyHtmlGui
        self._appInstance = pyHtmlGui.appInstance
        self._appViewClass = pyHtmlGui.appViewClass
        self._templateLoader = pyHtmlGui._templateLoader
        self._add_file_to_monitor = pyHtmlGui._add_file_to_monitor

        self._websocketInstances = []
        self._children = weakref.WeakSet()
        self._templateEnv = jinja2.Environment(loader=self._templateLoader)
        self._templateCache = {}
        self._call_number = 0
        self._call_javascript = self.call_javascript # so the call_javascript function in view is available
        self._function_references = WeakFunctionReferences()

        self._templateEnv.globals['_create_py_function_reference'] = self._create_function_reference

        self.view = self._appViewClass(self._appInstance, self)

    def update(self):
        self.call_javascript("pyhtmlgui.update_element", ["pyHtmlGuiBody", self.view.render()], skip_results=True)

    def set_visible(self, visible):
        if visible is False:
            for child in self._children:
                child.set_visible(False)
        if visible is True:
            self.update()

    # CALL JS FROM PY
    def call_javascript(self, js_function_name, args, skip_results = False):
        self._call_number += 1
        to_delete = self._call_number - 100 # clean old function references, this is needed to results don't stay around if you don't set skip_results=True and don't use the result.
        for websocketInstance in self._websocketInstances:
            if to_delete in websocketInstance.javascript_call_result_objects:
                del websocketInstance.javascript_call_result_objects[to_delete]
            if to_delete in websocketInstance.javascript_call_result_queues:
                del websocketInstance.javascript_call_result_queues[to_delete]

        javascript_call_object = {'call': self._call_number, 'name': js_function_name, 'args': args}

        if skip_results is True:
            javascriptCallResult = None
            javascript_call_object["skip_results"] = True
        else:
            javascriptCallResult = JavascriptCallResult(self._call_number)

        data = json.dumps(javascript_call_object, default=lambda o: None)
        for websocketInstance in self._websocketInstances:
            if skip_results is False:
                websocketInstance.javascript_call_result_objects[self._call_number] = javascriptCallResult
                javascriptCallResult._add_call(websocketInstance)
            websocketInstance.ws.send(data)
        return javascriptCallResult

    # MESSAGES FROM JS TO PY
    def websocket_loop(self, websocketInstance):
        self._websocketInstances.append(websocketInstance)
        while True:
            msg = websocketInstance.ws.receive()
            if msg is not None:
                message = json.loads(msg)
                gevent.spawn(self._websocket_process_message, message, websocketInstance).run()
            else:
                break
        self._websocketInstances.remove(websocketInstance)
        if len(self._websocketInstances) == 0:
            self.set_visible(False)

    def _websocket_process_message(self, message, websocketInstance):
        if 'call' in message:
            function_name = "Function not found"
            args = "  "
            try:
                if message['name'] == "frontend_ready":
                    function_name = "%s.update" % (self.__class__.__name__)
                    return_val = self.update()
                    self._pyHtmlGui._on_frontend_ready(self)

                elif message['name'] == "call_python_function":
                    functioncall_id = message['args'][0]
                    function = self._function_references.get(functioncall_id)
                    function_name = "%s.%s" % (function.__self__.__class__.__name__, function.__name__)
                    return_val = function()

                elif message['name'] == "call_python_function_with_args":
                    functioncall_id = message['args'][0]
                    args = message['args'][1]
                    function = self._function_references.get(functioncall_id)
                    function_name = "%s.%s" % (function.__self__.__class__.__name__, function.__name__)
                    return_val = function(*args)
                else:
                    return_val = None
                    print("unknown python function", message['name'] )

            except Exception as e:
                tb = traceback.format_exc()
                msg = " Exception in: %s(%s)\n" % ( function_name, ("%s" % args)[1:-1] )
                msg += " %s" % tb.replace("\n","\n  ").strip()
                self.call_javascript("pyhtmlgui.debug_msg", [msg])
                print(msg)
                return_val = None

            if not ("skip_results" in message and message["skip_results"] is True):
                websocketInstance.ws.send(json.dumps({ 'return': message['call'], 'value': return_val  }, default=lambda o: None))

        elif 'return' in message:
            call_id = message['return']
            del message['return'] # remove internal id from result before passing to next level
            if call_id in websocketInstance.javascript_call_result_objects:
                websocketInstance.javascript_call_result_objects[call_id]._result_received(websocketInstance, message)
        else:
            print('Invalid message received: ', message)

    def _create_function_reference(self, function):
        if type(function) == jinja2.runtime.Undefined:
            raise Exception("Undefined python method in script: '%s'" % function._undefined_name)
        cbid = self._function_references.add(function)
        return cbid

    def _get_template(self, item, force_reload = False):
        if force_reload is False:
            try:
                return self._templateCache[item.__class__.__name__]
            except:
                pass

        if item.__class__.TEMPLATE_FILE is not None:   # load from file
            file_to_monitor =  self._templateEnv.get_template(item.TEMPLATE_FILE).filename
            string_to_render = open(file_to_monitor, "r").read()
        else:   # load from class
            if self._pyHtmlGui.auto_reload is False:
                string_to_render = item.TEMPLATE_STR
                file_to_monitor  = None
            else:
                module_name = item.__module__
                if module_name is None or module_name == str.__class__.__module__:
                    module_fullname = item.__class__.__name__  # Avoid reporting __builtin__
                else:
                    module_fullname = module_name + '.' + item.__class__.__name__

                try:
                    file_to_monitor = os.path.abspath(inspect.getfile(item.__class__))
                except:  # in case its in mail, this may be a bug? in inspect
                    file_to_monitor = os.path.abspath(sys.argv[0])

                if module_name == "__main__":
                    name = os.path.splitext(os.path.basename(file_to_monitor))[0]
                    module = __import__(name)
                    importlib.reload(module) # reload should work on non complex objects in __main__, but not for more
                    for comp in module_fullname.split(".")[1:]:
                        module = getattr(module, comp)
                else:
                    loader = importlib.machinery.SourceFileLoader(module_name, file_to_monitor)
                    spec = importlib.util.spec_from_loader(loader.name, loader)
                    module = importlib.util.module_from_spec(spec)
                    loader.exec_module(module)
                    module = getattr(module, module_fullname.split(".")[-1])
                string_to_render = module.TEMPLATE_STR

        if self._pyHtmlGui.auto_reload is True:
            self._add_file_to_monitor(file_to_monitor, item.__class__.__name__)

        # replace pyhtmlgui.call(python_function, "arg1") with pyhtmlgui.call({{_create_py_function_reference(python_function)}}, "arg1")
        # this a a convinience function is user does not have to type the annoying stuff and functions look cleaner
        parts = re.split(r'(>| |\(|=|\"|\'|\n|\r|\t|;)(pyhtmlgui\.call\(.+?)(,|\))', string_to_render)
        for i in [i for i, part in enumerate(parts) if part.startswith("pyhtmlgui.call(")]:
            parts[i] = "pyhtmlgui.call({{_create_py_function_reference(%s)}}" % parts[i][15:]
        string_to_render = "".join(parts)

        # use \pyhtmlgui.call to excape pyhtmlgui.call in case of for example <div>Usage: pyhtmlgui.call(this.foobar, "arg1") </div> where the function should not be called
        string_to_render = string_to_render.replace('\pyhtmlgui.call(', 'pyhtmlgui.call(')
        try:
            self._templateCache[item.__class__.__name__] = self._templateEnv.from_string(string_to_render)
        except Exception as e:
            msg = "Failed to load Template "
            if item.TEMPLATE_FILE is not None:
                msg += "from File '%s': " % item.TEMPLATE_FILE
            else:
                msg += "from Class '%s': " % item.__class__.__name__
            msg += " %s" % e
            raise Exception(msg)

        return self._templateCache[item.__class__.__name__]

    def clear_template_cache(self, classnames = None):
        if classnames is None:
            self._templateCache = {}
        else:
            for classname in classnames:
                try:
                    del self._templateCache[classname]
                except:
                    pass

    def _add_child(self, child):
        self._children.add(child)

    def _remove_child(self, child):
        self._children.remove(child)

class JavascriptCallResult():
    def __init__(self, call_id):
        self.call_id = call_id
        self.websocketInstances = weakref.WeakSet()
        self._results_missing = 0
        self._callback = None

    def _add_call(self, websocketInstance):
        websocketInstance.javascript_call_result_queues[self.call_id] = queue.Queue()
        self.websocketInstances.add(websocketInstance)
        self._results_missing += 1

    def _result_received(self, websocketInstance, result):
        websocketInstance.javascript_call_result_queues[self.call_id].put(result)
        self._results_missing -= 1
        if self._results_missing == 0 and self._callback != None:
            self._callback(self._collect_results())

    def _collect_results(self):
        results  = []
        for websocketInstance in self.websocketInstances:
            results.append(websocketInstance.javascript_call_result_queues[self.call_id].get())
            del websocketInstance.javascript_call_result_queues[self.call_id]
            del websocketInstance.javascript_call_result_objects[self.call_id]  # remove ourself from websocket callback list
        errors = [result["error"] for result in results if "error" in result]
        if len(errors) > 0:
            msg = "%s of %s connected frontends returned an error\n" % (len(errors), len(results))
            msg += "\n".join(errors)
            raise Exception(msg)
        return [result["value"] for result in results]

    def __call__(self, callback = None):
        if callback is None:
            return self._collect_results()
        else:
            if self._results_missing == 0:
                callback(self._collect_results())
            else:
                self._callback = callback