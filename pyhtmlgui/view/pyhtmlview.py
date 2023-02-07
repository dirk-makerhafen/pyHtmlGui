from __future__ import annotations
import time
import typing
import weakref
import traceback
import random
import string
import logging
from markupsafe import Markup
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyhtmlgui.lib.observable import Observable
from pyhtmlgui.pyhtmlguiInstance import PyHtmlGuiInstance

CHARACTERS = list(string.ascii_lowercase + string.digits)


class PyHtmlView:
    TEMPLATE_STR  = None
    TEMPLATE_FILE = None
    DOM_ELEMENT = "div"
    DOM_ELEMENT_CLASS = ""
    DOM_ELEMENT_EXTRAS = ""

    def __init__(self, subject, parent:  typing.Union[PyHtmlView, PyHtmlGuiInstance], **kwargs):
        self.uid = "pv%s" % ("".join(random.choices(CHARACTERS, k=16)))
        self.is_visible = False

        parent._add_child(self)
        self._subject_wref = weakref.ref(subject, self._on_subject_died)
        self._parent_wref = weakref.ref(parent, None)

        self._instance = parent if type(parent) == PyHtmlGuiInstance else parent._instance
        self._was_rendered = False
        self._last_rendered = 0
        self._observables = ObservableMappings()
        self._children = weakref.WeakSet()
        self._subject = None  # this is replace for a short time on render by the actual resolved object

        if self._on_subject_updated is not None: # by default we observe the subject
            try:
                self.add_observable(self.subject)
            except Exception as e:
                logging.warning("object type '%s' can not be observed, %s" % (type(subject),e))

    @property
    def subject(self):
        if self._subject is not None:
            return self._subject
        return self._subject_wref()

    @property
    def parent(self):
        return self._parent_wref()

    def _on_subject_updated(self, source, **kwargs) -> None:
        self.update()

    def _on_subject_died(self, wr) -> None:
        self.delete()

    def render(self) -> typing.Union[str, None]:
        """
            Return object rendered to html string. This function should be called from inside the jinja templates.
            Direct usage is not needed, Returns html string rendered from template
        """
        self._subject = self.subject  # receive hard reference to obj so it does not die on us while rendering
        if self._subject is None:  # Observed object died before render
            return None

        if self.is_visible is False:
            self.set_visible(True)

        for child in self._children:
            try:
                child._was_rendered = False
            except:
                pass

        try:
            html = self._instance.get_template(self).render({"pyview": self})
        except Exception:
            html = " Exception while rendering Template: %s\n %s" % (self.__class__.__name__, traceback.format_exc().replace("\n", "\n  ").strip())
            self._instance.call_javascript("pyhtmlgui.debug_msg", [html])
            logging.error(html)

        for child in self._children:
            try:
                if child._was_rendered is False and child.is_visible is True:
                    child.set_visible(False)
            except Exception as e:
                print(e)
                pass

        self._was_rendered = True
        self._last_rendered = time.time()
        self._subject = None  # remove hard reference to subject, it may die now

        if html is None:
            return None
        if self.DOM_ELEMENT is None:
            return Markup(html)
        else:
            cls = self.DOM_ELEMENT_CLASS
            if cls == "":   cls = self.__class__.__name__
            if cls is None: cls = ""
            if cls != "":   cls = 'class="%s"' % cls
            return Markup('<%(el)s %(cls)s id="%(uid)s" %(ex)s>%(html)s</%(el)s>' % {
                "el"  : self.DOM_ELEMENT,
                "cls" : cls,
                "uid" : self.uid,
                "ex"  : self.DOM_ELEMENT_EXTRAS,
                "html": html,
            })

    def update(self) -> None:
        """
        update rendered view in DOM, must be visible
        """
        if self.is_visible is True:
            html_content = self.render()
            if html_content is not None:  # object might have died, in that case don't render
                self._instance.call_javascript("pyhtmlgui.replace_element", [self.uid, html_content], skip_results=True)
        else:
            logging.warning("Can't update invisible components")

    def insert_element(self, index: int, element: PyHtmlView) -> bool:
        """
        Insert a new element into DOM at index.
        This is used for example in ObservableDictView and ObservableListView to insert newly created elements.
        """
        html_content = element.render()
        if html_content is not None:  # object might have died, in that case don't render
            self._instance.call_javascript("pyhtmlgui.insert_element", [self.uid, index, html_content], skip_results=True)
            return True
        return False

    def move_element(self, index: int, element: PyHtmlView) -> bool:
        """
        Move existing element to position index.
        This is used for example in ObservableDictView and ObservableListView to reorder elements without rerendering.
        """
        self._instance.call_javascript("pyhtmlgui.move_element", [self.uid, index, element.uid], skip_results=True)
        return True

    def delete(self, remove_from_dom: bool = True) -> None:
        """
        Delete element, detach events, remove from parent, remove from frontend if element is visible

        :param remove_from_dom: If parent element calls delete, remove_from_dom is set to False,
                                because parent removes itself + all childen from dom automatically
        """
        if self.is_visible is True and remove_from_dom is True:
            self._instance.call_javascript("pyhtmlgui.remove_element", [self.uid], skip_results=True)
        self.set_visible(False)
        try:
            self.parent._remove_child(self)
        except:
            pass
        self._children.clear()

    def set_visible(self, visible: bool) -> None:
        """
        Set component and childens visibility, components that are not visible get their events detached
        """
        if self.is_visible == visible:
            return

        if visible is False:
            self.is_visible = False
            self._observables.disable()
            for child in self._children:
                try:
                    child.set_visible(False)
                except:
                    pass
        else:
            self.is_visible = True
            self._observables.enable()

    def call_javascript(self, js_function_name, args=None, skip_results=False):
        """
        Call javascript function in frontend.
        :param js_function_name: Name of javascript function
        :param args: Arguments for js function
        :param skip_results: Don't receive results, give some slight performance inprovement because
                             we don't wait for results
        """
        if self.is_visible is False:
            logging.warning("Can't javascript_call invisible components")
            return
        return self._instance.call_javascript(js_function_name, args, skip_results)

    def eval_javascript(self, script, skip_results=False, **kwargs):
        """
        Run script in frontend.
        :param script: Javascript source code
        :param skip_results: Don't receive results, give some slight performance inprovement because
                             we don't wait for results
        :param kwargs: kwargs are passed to javascript as "arg" variable
        :return:
        """
        if self.is_visible is False:
            logging.warning("Can't javascript_call invisible components")
            return
        return self._instance.call_javascript("pyhtmlgui.eval_script", [script, kwargs], skip_results=skip_results)

    def _add_child(self, child: PyHtmlView) -> None:
        self._children.add(child)

    def _remove_child(self, child: PyHtmlView) -> None:
        try:
            self._children.remove(child)
        except: # ignore if weak ref faild to resolve
            pass

    def add_observable(self, subject: Observable, target_function: typing.Callable = None) -> None:
        if target_function is None:
            target_function = self._on_subject_updated
        self._observables.add(subject,target_function)

    def remove_observable(self, subject: Observable, target_function: typing.Callable = None) -> None:
        if target_function is None:
            target_function = self._on_subject_updated
        self._observables.remove(subject, target_function)

    def set_autoupdate_interval(self, interval):
        if interval is not None and interval < 1:
            raise Exception("Interval must be at least 1 second")
        self._autoupdate_interval = interval
        if self._autoupdate_interval is not None:
            self._instance._add_polling_child(self)
        else:
            self._instance._remove_polling_child(self)


class ObservableMappings():
    def __init__(self):
        self.mappings = []

    def add(self, subject, target):
        try:
            if not callable(subject.attach_observer) or not callable(subject.detach_observer):
                raise Exception("object type '%s' can not be observed" % type(subject))
        except Exception:
            raise Exception("object type '%s' can not be observed" % type(subject))
        self.mappings.append(ObservableMapping(self, subject, target))

    def get(self, subject, target):
        for mapping in self.mappings:
            try:
                if subject == mapping.observable():
                    if target is None or target == mapping.function():
                        return mapping
            except:
                pass
        return None

    def remove(self, subject, target):
        mapping = self.get(subject, target)
        if mapping is not None:
            try:
                mapping.disable()
                self.mappings.remove(mapping)
            except:
                pass

    def enable(self):
        for m in self.mappings:
            m.enable()

    def disable(self):
        for m in self.mappings:
            m.disable()

    def _child_died(self, child):
        try:
            self.mappings.remove(child)
        except:
            pass


class ObservableMapping():
    def __init__(self, parent, subject, target):
        self.parent = parent
        self.subject = weakref.ref(subject, self._on_subject_died)
        self.target = weakref.WeakMethod(target, self._on_target_died)

    def enable(self):
        try: # objects might die on us
            self.subject().attach_observer(self.target())
        except:
            pass

    def disable(self):
        try:  # objects might die on us
            self.subject().detach_observer(self.target())
        except:
         pass

    def _on_subject_died(self, *args):
        self.parent._child_died(self)

    def _on_target_died(self, *args):
        self.parent._child_died(self)

