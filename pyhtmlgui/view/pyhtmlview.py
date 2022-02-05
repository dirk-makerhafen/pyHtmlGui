import weakref
import uuid
import traceback
import time


class PyHtmlView():
    TEMPLATE_FILE = None
    TEMPLATE_STR = None
    WRAPPER_ELEMENT = "pyHtmlView"
    WRAPPER_EXTRAS = ""

    def __init__(self, subject, parent):

        # Component state and data
        self.uid = "%s" % uuid.uuid4()
        self.is_visible = False
        self._children = weakref.WeakSet()

        # Weak references to  subject, parent
        if type(parent) == weakref.ref:
            parent = parent()
        if type(subject) == weakref.ref:
            subject = subject()

        self._subject_wref = None
        self._parent_wref = None
        self._subject = None  # this is replace for a short time on render by the actual resolved object
        if subject is not None:
            self._subject_wref = weakref.ref(subject, self._on_subject_died)  # non gui object we reprecent or talk to
        if parent is not None:
            parent._add_child(self)
            self._parent_wref = weakref.ref(parent, None)  # parent of this element

        # get template loader function from parent
        self._get_template = parent._get_template
        self._was_rendered = True
        self._last_rendered = None  # timestamp of last rendering, for debug only

        self._call_javascript = parent._call_javascript  # root element gets this supplied by pyhtmlgui lib, else none
        self._observables = []

        # attach default observation event and detach because default componens is invisible until rendered
        if self._on_subject_updated is not None:
            try:
                self.add_observable(self.subject)
            except Exception as e:  # detach all will thow an exception if the event can not be attached
                print(e)
                print("object type '%s' can not be observed" % type(subject))

    @property
    def subject(self):
        if self._subject is not None:
            return self._subject
        return self._subject_wref()

    @property
    def parent(self):
        return self._parent_wref()

    def _on_subject_updated(self, source, **kwargs):
        self.update()

    def _on_subject_died(self, wr):
        self.delete()

    # return html string rendered from template
    # automatically set component to visible
    def render(self):
        html = self._inner_html()
        if html is None:
            return None
        self._last_rendered = time.time()
        if self.WRAPPER_ELEMENT is None:
            return html
        else:
            return "<%s id='%s' %s data-pyhtmlgui-class='%s'>%s</%s>" % (
                self.WRAPPER_ELEMENT, self.uid, self.WRAPPER_EXTRAS, self.__class__.__name__, html,
                self.WRAPPER_ELEMENT)

    # update rendered component in place, must be visible
    def update(self):
        if self.is_visible is True:
            html_content = self.render()
            if html_content is not None:  # object might have died, in that case don't render
                self.call_javascript("pyhtmlgui.replace_element", [self.uid, html_content], skip_results=True)
        else:
            raise Exception("Can't update invisible components")

    def insert_element(self, index, element):
        html_content = element.render()
        if html_content is not None:  # object might have died, in that case don't render
            self.call_javascript("pyhtmlgui.insert_element", [self.uid, index, html_content], skip_results=True)
            return True
        return False

    # detach events, remove from parent, remove from frontend if is visible
    def delete(self, already_removed_from_dom=False):
        if self.is_visible is True and already_removed_from_dom is False:
            self.call_javascript("pyhtmlgui.remove_element", [self.uid], skip_results=True)
        self.set_visible(False)
        self.parent._remove_child(self)
        for child in self._children:
            child.delete(already_removed_from_dom=True)

    # set component and childens visibility
    # components that are not visible get their events detached
    def set_visible(self, visible):
        if self.is_visible == visible:
            return

        if visible is False:
            self.is_visible = False
            for observable, target in self._observables:
                try:
                    observable().detach_observer(target())  # resolve weak references
                except:
                    pass
            for child in self._children:
                child.set_visible(False)
        else:
            self.is_visible = True
            for observable, target in self._observables:
                try:
                    observable().attach_observer(target())  # resolve weak references
                except:
                    pass

    # function so we have function arguments name completion in editor,
    # in theorie we could directly use self._call_javascript
    def call_javascript(self, js_function_name, args, skip_results=False):
        return self._call_javascript(js_function_name, args, skip_results)

    # this is a convinience function, you could also call the subcall directly
    def eval_javascript(self, script, skip_results=False, **kwargs):
        if self.is_visible is False:
            raise Exception("Can't javascript_call invisible components")
        return self.call_javascript("pyhtmlgui.eval_script", [script, kwargs], skip_results=skip_results)

    def eval_javascript_electron(self, script, skip_results=False, **kwargs):
        if self.is_visible is False:
            raise Exception("Can't javascript_call invisible components")
        return self.call_javascript("electron.eval_script", [script, kwargs], skip_results=skip_results)

    def _inner_html(self):
        self._subject = self.subject  # receive hard reference to obj to it does not die on us while rendering
        if self._subject is None:  # Observed oject died before render
            return None
        # It should be ok to set visible here, althou this is befor the rendered object actually appeart in the dom.
        # However, it should arrive at to dom before any other things that might be triggered because the object is visible,
        # because of the websocket event loop
        self.set_visible(True)
        for child in self._children:
            child._was_rendered = False

        try:
            html = self._get_template(self).render({"pyview": self})
        except Exception as e:
            tb = traceback.format_exc()
            msg = " Exception while rendering Template: %s\n" % self.__class__.__name__
            msg += " %s" % tb.replace("\n", "\n  ").strip()
            self.call_javascript("pyhtmlgui.debug_msg", [msg])
            html = msg
            print(msg)

        # set children that have not been rendered in last pass to invisible
        [c.set_visible(False) for c in self._children if c._was_rendered is False and c.is_visible is True]

        self._was_rendered = True
        self._subject = None  # remove hard reference to subject, it may die now
        return html

    def _add_child(self, child):
        self._children.add(child)

    def _remove_child(self, child):
        self._children.remove(child)

    # default target_function is  self._on_subject_updated
    def add_observable(self, subject, target_function=None):
        try:
            if not callable(subject.attach_observer) or not callable(subject.detach_observer):
                raise Exception("object type '%s' can not be observed" % type(subject))
        except:
            raise Exception("object type '%s' can not be observed" % type(subject))
        if target_function is None:
            target_function = self._on_subject_updated

        if type(subject) != weakref.ref:
            subject = weakref.ref(subject)
        if type(target_function) != weakref.WeakMethod:
            target_function = weakref.WeakMethod(target_function)
        self._observables.append([subject, target_function])

    def remove_observable(self, subject, target_function=None):
        if target_function is None:
            target_function = self._on_subject_updated
        to_remove = []
        for e in self._observables:
            e_subject, e_target_function = e
            if subject == e_subject():
                if target_function is None or target_function == e_target_function():
                    to_remove.append(e)
        for e in to_remove:
            self._observables.remove(e)
