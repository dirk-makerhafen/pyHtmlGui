import weakref
from .lib import EventMap
import  uuid
import queue
import re, os

class pyHtmlGuiComponent():
    TEMPLATE_FILE = None
    TEMPLATE_STR = None

    def __init__(self, observedObject, parentComponent):

        # Component state and data
        self.uid = "%s" % uuid.uuid4()
        self._visible = False
        self._children = weakref.WeakSet()

        # Weak references to  observedObject, parentComponent
        if type(parentComponent) == weakref.ref:
            parentComponent = parentComponent()
        if type(observedObject) == weakref.ref:
            observedObject = observedObject()

        self._observedObject_wref = None
        self._parentComponent_wref = None
        if observedObject is not None:
            self._observedObject_wref = weakref.ref(observedObject,self._on_observedObject_died)  # non gui object we reprecent or talk to
        if parentComponent is not None:
            parentComponent._add_child(self)
            self._parentComponent_wref = weakref.ref(parentComponent, self._on_parentComponent_died)  # parent of this element

        # Load Templates
        self._templateEnv  = self.parentComponent._templateEnv
        if self.TEMPLATE_FILE is not None:
            self.TEMPLATE_STR = open( os.path.join(self.parentComponent.template_dir, self.TEMPLATE_FILE),"r").read()
        self._template = self._templateEnv.from_string(self.TEMPLATE_STR)

        self._event_queue = parentComponent._event_queue # root element gets this supplied by pyHtmlGui lib, else none

        self.event_map = EventMap()

        #attach default observation event
        try:
            observedObject.attachObserver(self._on_default_event_updated)
        except:
            print("object can not be observed")

    def _on_default_event_updated(self,  *kwargs):
        print("event received")
        self.update()


    @property
    def observedObject(self):
        return self._observedObject_wref()

    @property
    def parentComponent(self):
        return self._parentComponent_wref()

    def _on_observedObject_died(self, wr):
        print("observedObject died", wr)
        raise NotImplementedError()

    def _on_parentComponent_died(self, wr):
        print("Parent died", wr)
        raise NotImplementedError()



    # return html string rendered from template
    # automatically set component to visible
    def render(self):
        self.set_visible(True)
        print("render called:", self)
        html = self._template.render({"this": self})
        html = html.replace("$this", '$("#%s")' % self.uid)
        return "<pyHtmlGui id='%s'>%s</pyHtmlGui>" % (self.uid, html)

    # update rendered component in place, must be visibie
    def update(self):
        if self._visible is True:
            self._event_queue.put(("render", self.uid, self))
        else:
            raise Exception("Can't update invisible components")

    def javascript_call(self, javascript, callback = None):
        if self._visible is False:
            raise Exception("Can't javascript_call invisible components")

        javascript = javascript.replace("$this", '$("#%s")' % self.uid)

        if callback is None:
            result_queue = queue.Queue()
            def cb(result):
                result_queue.put(result)
            self._event_queue.put(["javascript_call", "run_javascript", [javascript], cb])
            def rf():
                return result_queue.get()
            return rf
        else:
            self._event_queue.put(["javascript_call", "run_javascript", [javascript], callback])

    def delete(self):
        self.event_map.detach_all()
        self.parentComponent._remove_child(self)
        for child in self._children:
            child.delete()

    # set component and childens visibilits
    # components that are not visible get their events detached
    def set_visible(self, visible):
        if self._visible is True:
            if visible is False:
                self._visible = False
                self.event_map.detach_all()
                for child in self._children:
                    child.set_visible(visible)
        else:
            if visible is True:
                self._visible = True
                self.event_map.attach_all()

    def _add_child(self, child):
        self._children.add(child)

    def _remove_child(self, child):
        self._children.remove(child)



class DictWrapperComponent():
    def __init__(self, root, parent, templateEnv,  observable_dict, wrapper_class, **kwargs ):
        self.root = root
        self.parent = parent
        self.templateEnv = templateEnv
        self.observable_dict = observable_dict
        self.wrapper_class = wrapper_class
        self.kwargs = kwargs

        self._wrapped_data = {}
        observable_dict.attach(self.on_obj_event)
        for key, item in observable_dict.items():
            self._wrapped_data[key] = self.wrapper_class(self.root, self.parent, item, self.templateEnv, **self.kwargs)

    def on_obj_event(self, event): # FIXME add this
        print("DICT ACTION", event)
        if event.action == "inserted":
            self._wrapped_data[event.key] = self.wrapper_class(self.root, self.parent, event.item, self.templateEnv, **self.kwargs)

        if event.action == "removed":
            self._wrapped_data[event.key].delete()

    def get(self):
        return self._wrapped_data


class ListWrapperComponent():
    def __init__(self, root, parent, templateEnv,  observable_list, wrapper_class, **kwargs ):
        self.root = root
        self.parent = parent
        self.templateEnv = templateEnv
        self.observable_list = observable_list
        self.wrapper_class = wrapper_class
        self.kwargs = kwargs

        self._wrapped_data = []
        for item in observable_list:
            self._wrapped_data.append(self.wrapper_class(self.root, self.parent, item, self.templateEnv, **self.kwargs))

    def on_obj_event(self, event):
        if event.action == "inserted":
            self._wrapped_data.append( self.wrapper_class(self.root, self.parent, event.item, self.templateEnv, **self.kwargs))

        if event.action == "removed":
            raise Exception("remove tood")

    def get(self):
        return self._wrapped_data

