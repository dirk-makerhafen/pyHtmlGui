import types
import weakref
import uuid
import traceback
from threading import Lock
from .lib import EventSet
import time

class PyHtmlView():
    TEMPLATE_FILE = None
    TEMPLATE_STR = None
    WRAPPER_ELEMENT = "pyHtmlView"

    def __init__(self, observedObject, parentView):

        # Component state and data
        self.uid = "%s" % uuid.uuid4()
        self.is_visible = False
        self._children = weakref.WeakSet()

        # Weak references to  observedObject, parentView
        if type(parentView) == weakref.ref:
            parentView = parentView()
        if type(observedObject) == weakref.ref:
            observedObject = observedObject()

        self._observedObject_wref = None
        self._parentView_wref = None
        self._observedObject = None # this is replace for a short time on render by the actual resolved object
        if observedObject is not None:
            self._observedObject_wref = weakref.ref(observedObject,self._on_observedObject_died)  # non gui object we reprecent or talk to
        if parentView is not None:
            parentView._add_child(self)
            self._parentView_wref = weakref.ref(parentView, self._on_parentView_died)  # parent of this element

        # get template loader function from parent
        self._get_template  = parentView._get_template
        self.__was_rendered__ = True
        self.__last_rendered = None # timestamp of last rendering, for debug only

        self._call_javascript = parentView._call_javascript # root element gets this supplied by pyhtmlgui lib, else none
        self.events = EventSet()

        #attach default observation event and detach because default componens is invisible until rendered
        if self._on_observedObject_updated is not None:
            try:
                self.events.add(self.observedObject, self._on_observedObject_updated)
            except Exception as e: # detach all will thow an exception if the event can not be attached
                print(e)
                print("object type '%s' can not be observed" % type(observedObject))



    @property
    def observedObject(self):
        if self._observedObject is not None:
            return self._observedObject
        return self._observedObject_wref()

    @property
    def parentView(self):
        return self._parentView_wref()

    def _on_observedObject_updated(self, source, **kwargs):
        self.update()

    def _on_observedObject_died(self, wr):
        print("observedObject died", wr)
        #raise NotImplementedError()

    def _on_parentView_died(self, wr):
        print("Parent died", wr)
        raise NotImplementedError()

    # return html string rendered from template
    # automatically set component to visible
    def render(self):
        html = self._inner_html()
        if html == None:
            return None
        self.__last_rendered = time.time()
        if self.WRAPPER_ELEMENT is None:
            return html
        else:
            return "<%s id='%s' data-pyhtmlgui-class='%s'>%s</%s>" % (self.WRAPPER_ELEMENT, self.uid, self.__class__.__name__, html, self.WRAPPER_ELEMENT)

    def _inner_html(self):
        self._observedObject = self.observedObject # receive hard reference to obj to it does not die on us while rendering
        if self._observedObject is None:
            print("Observed oject died before render")
            return None
        self.set_visible(True) # It should be ok to set visible here, althou this is befor the rendered object actually appeart in the dom. However, it should arrive at to dom before any other things that might be triggered because the object is visible, because of the websocket event loop
        for child in self._children: child.__was_rendered__ = False
        try:
            html = self._get_template(self).render({"this": self})
        except Exception as e:
            tb = traceback.format_exc()
            msg = " Exception while rendering Template: %s\n" % self.__class__.__name__
            msg += " %s" % tb.replace("\n", "\n  ").strip()
            self.call_javascript("pyhtmlgui.debug_msg", [msg])
            html = msg
            print(msg)

        [c.set_visible(False) for c in self._children if c.__was_rendered__ is False and c.is_visible is True] # set children that have not been rendered in last pass to invisible
        self.__was_rendered__ = True
        self._observedObject = None # remove hard reference to observedobject, it may die now
        return html

    # update rendered component in place, must be visibie
    def update(self):
        if self.is_visible is True:
            html_content = self.render()
            if html_content is not None: # object might have died, in that case don't render
                self.call_javascript("pyhtmlgui.replace_element", [self.uid, html_content], skip_results=True)
        else:
            raise Exception("Can't update invisible components")

    # detach events, remove from parent, remove from frontend if is visible
    def delete(self, already_removed_from_dom = False):
        self.events.detach_all()
        if self.is_visible is True and already_removed_from_dom is False:
            self.call_javascript("pyhtmlgui.remove_element", [self.uid], skip_results=True)
        self.parentView._remove_child(self)
        for child in self._children:
            child.delete(already_removed_from_dom = True)

    # insert this rendered element into parent node at index
    def insert_element(self, index):
        html_content = self.render()
        if html_content is not None:  # object might have died, in that case don't render
            self.call_javascript("pyhtmlgui.insert_element", [self.parentView.uid, index, html_content], skip_results=True)

    # function so we have function arguments name completion in editor, in theorie we could directly use self._call_javascript
    def call_javascript(self, js_function_name, args, skip_results=False):
        return self._call_javascript(js_function_name, args, skip_results)

    # this is a convinience function, you could also call the subcall directly
    def eval_javascript(self, script, skip_results = False, **kwargs):
        if self.is_visible is False:
            raise Exception("Can't javascript_call invisible components")
        return self.call_javascript("pyhtmlgui.eval_script", [script, kwargs], skip_results=skip_results)

    def eval_javascript_electron(self, script, skip_results = False, **kwargs):
        if self.is_visible is False:
            raise Exception("Can't javascript_call invisible components")
        return self.call_javascript("electron.eval_script", [script, kwargs], skip_results=skip_results)

    # set component and childens visibility
    # components that are not visible get their events detached
    def set_visible(self, visible):
        if self.is_visible == visible:
            return

        if visible is False:
            self.is_visible = False
            self.events.detach_all()
            for child in self._children:
                child.set_visible(False)
        else:
            self.is_visible = True
            self.events.attach_all()# don't set children to visible here, because that happens if their render() function is called

    def _add_child(self, child):
        self._children.add(child)

    def _remove_child(self, child):
        self._children.remove(child)


class ObservableDictView(PyHtmlView):
    TEMPLATE_STR = '''
        {% for item in this.get_items() %}
            {{ item.render()}}
        {% endfor %}
    '''
    def __init__(self, observedObject, parentView, item_class, wrapper_element = PyHtmlView.WRAPPER_ELEMENT, sort_lambda=None, sort_reverse=False, **kwargs):
        self._item_class = item_class
        self.WRAPPER_ELEMENT = wrapper_element
        self._kwargs = kwargs
        self._wrapped_data = {}
        self._wrapped_data_lock = Lock()
        self.sort_lambda = sort_lambda
        self.sort_reverse = sort_reverse
        super().__init__(observedObject, parentView)

    def set_visible(self, visible):
        if self.is_visible == visible: # not changed
            return
        self._wrapped_data_lock.acquire()
        super().set_visible(visible)
        self._wrapped_data = {}
        if self.is_visible is True: # was set to invisible
            for kv in self.observedObject.items():
                key, item = kv
                self._wrapped_data[key] = self._create_item(item, key)
        self._wrapped_data_lock.release()

    def get_items(self):
        items = [item for key, item in self._wrapped_data.items()]
        if self.sort_lambda is None:
            return sorted(items, key=lambda x: x.item_key)
        else:
            return sorted(items, key=lambda x:self.sort_lambda, reverse=self.sort_reverse)

    def _create_item(self, item, key):
        obj = self._item_class(item, self, **self._kwargs)
        obj.item_key = key
        return obj

    def _on_observedObject_updated(self, source, **kwargs):
        try:
            self._wrapped_data_lock.acquire()

            if kwargs["action"] == "setitem":
                if kwargs["key"] in self._wrapped_data:
                    self._wrapped_data[kwargs["key"]].delete() # unrender
                obj = self._create_item(kwargs["item"], kwargs["key"])
                self._wrapped_data[kwargs["key"]] = obj
                index = list(self._wrapped_data.keys()).index(kwargs["key"])
                if obj.insert_element(index) is False:
                    del self._wrapped_data[kwargs["key"]]

            if kwargs["action"] == "update":
                for kv in kwargs["items"]:
                    key, item = kv
                    obj = self._create_item(item, kwargs["key"])
                    if key in self._wrapped_data:
                        self._wrapped_data[key].delete()  # unrender
                    self._wrapped_data[key] = obj
                    index = list(self._wrapped_data.keys()).index(kwargs["key"])
                    if obj.insert_element(index) is False:
                        del self._wrapped_data[kwargs["key"]]

            if kwargs["action"] in [ "delitem", "pop", "popitem"]:
                self._wrapped_data[kwargs["key"]].delete()
                del self._wrapped_data[kwargs["key"]]

            if kwargs["action"] == "clear":
                for key, item in self._wrapped_data.items():
                    item.delete()
                self._wrapped_data.clear()
                self.update()

        finally:
            self._wrapped_data_lock.release()


class ObservableListView(PyHtmlView):
    TEMPLATE_STR = '''
        {% for item in this.get_items() %}
            {{ item.render()}}
        {% endfor %}
    '''
    def __init__(self, observedObject, parentView, item_class, wrapper_element = PyHtmlView.WRAPPER_ELEMENT, sort_lambda=None, sort_reverse=False, filter= None, **kwargs):
        self._item_class = item_class
        self.WRAPPER_ELEMENT = wrapper_element
        self._kwargs = kwargs
        self._wrapped_data = []
        self._wrapped_data_lock = Lock()
        self.sort_lambda = sort_lambda
        self.sort_reverse = sort_reverse
        self.filter = filter
        if self.filter is None:
            self.filter = lambda x: False
        super().__init__(observedObject, parentView)

    def get_items(self):
        data = [w for w in self._wrapped_data if self.filter(w) is False]
        if self.sort_lambda is None:
            return data
        else:
            return sorted(data, key=lambda x:self.sort_lambda, reverse=self.sort_reverse)

    def set_visible(self, visible):
        if self.is_visible == visible: # not changed
            return
        self._wrapped_data_lock.acquire()
        super().set_visible(visible)
        self._wrapped_data = []
        if self.is_visible is True: # was set to invisible
            for item in self.observedObject:
                self._wrapped_data.append(self._create_item(item))
        self._wrapped_data_lock.release()

    def _create_item(self, item):
        obj = self._item_class(item, self, **self._kwargs)
        obj.loop_index = types.MethodType(lambda x: x.parentView._loop_index(x), obj)
        obj.loop_index_used = False
        return obj

    def _on_observedObject_updated(self, source, **kwargs):
        try:
            self._wrapped_data_lock.acquire()

            if kwargs["action"] in ["append", "insert"]:
                obj = self._create_item(kwargs["item"])
                self._wrapped_data.insert(kwargs["index"], obj)
                if self.filter(obj) is False:
                    if obj.insert_element(kwargs["index"]) is False:
                        self._wrapped_data.remove(obj)
                    else:
                        [item.update() for item in self._wrapped_data[kwargs["index"]+1:] if item.loop_index_used == True] # update items that use the loop index

            if kwargs["action"] == "setitem":
                self._wrapped_data[kwargs["index"]].delete() # unrender
                obj = self._create_item(kwargs["newItem"])
                self._wrapped_data[kwargs["index"]] = obj
                if self.filter(obj) is False:
                    if obj.insert_element(kwargs["index"]) is False:
                        self._wrapped_data.remove(obj)

            if kwargs["action"] == "extend":
                current_index = kwargs["index"]
                for item in kwargs["items"]:
                    obj = self._create_item(item)
                    self._wrapped_data.insert(current_index, obj)
                    if self.filter(obj) is False:
                        if obj.insert_element(kwargs["index"]) is False:
                            self._wrapped_data.remove(obj)
                        else:
                            current_index += 1
                [item.update() for item in self._wrapped_data[current_index:] if item.loop_index_used == True]

            if kwargs["action"] in [ "remove", "pop", "delitem"]:
                self._wrapped_data[kwargs["index"]].delete()
                del self._wrapped_data[kwargs["index"]]
                [item.update() for item in self._wrapped_data[kwargs["index"]:] if item.loop_index_used == True]

            if kwargs["action"] == "sort":
                self.update()
            if kwargs["action"] == "reverse":
                self.update()
        finally:
            self._wrapped_data_lock.release()

    def _loop_index(self, element):
        element.loop_index_used = True
        return self._wrapped_data.index(element)
