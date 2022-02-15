from __future__ import annotations
import typing
import weakref
import traceback
import time
import random
import string
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

    def __init__(self,
                 subject,
                 parent:  typing.Union[PyHtmlView, PyHtmlGuiInstance],
                 **kwargs):

        self.uid = "pv%s" % ("".join(random.choices(CHARACTERS, k=16)))
        self.is_visible = False

        parent._add_child(self)
        self._subject_wref = weakref.ref(subject, self._on_subject_died)
        self._parent_wref = weakref.ref(parent, None)

        self._subject = None  # this is replace for a short time on render by the actual resolved object
        self._children = weakref.WeakSet()
        self._observables = []
        self.__last_rendered = None  # timestamp of last rendering, for debug only
        self.__was_rendered = False

        if type(parent) == PyHtmlGuiInstance:
            self._instance = parent
        else:
            self._instance = parent._instance

        # attach default observation event and detach because default componens is invisible until rendered
        if self._on_subject_updated is not None:
            try:
                self.add_observable(self.subject)
            except Exception:  # detach all will thow an exception if the event can not be attached
                print("object type '%s' can not be observed" % type(subject))

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

    # noinspection PyUnusedLocal
    def _on_subject_died(self, wr) -> None:
        self.delete()

    def render(self) -> typing.Union[str, None]:
        """
            Return object rendered to html string. This function should be called from inside the jinja templates.
            Direct usage is not needed, Returns html string rendered from template
        """
        html = self._inner_html()
        if html is None:
            return None
        self.__last_rendered = time.time()
        if self.DOM_ELEMENT is None:
            return html
        else:
            cls = self.DOM_ELEMENT_CLASS
            if cls == "":   cls = self.__class__.__name__
            if cls is None: cls = ""
            if cls != "":   cls = 'class="%s"' % cls

            s = '<%(el)s %(cls)s id="%(uid)s" %(ex)s>%(html)s</%(el)s>'
            return s % {
                "el"  : self.DOM_ELEMENT,
                "cls" : cls,
                "uid" : self.uid,
                "ex"  : self.DOM_ELEMENT_EXTRAS,
                "html": html,
            }

    def update(self) -> None:
        """
        update rendered view in DOM, must be visible
        """
        if self.is_visible is True:
            html_content = self.render()
            if html_content is not None:  # object might have died, in that case don't render
                self.call_javascript("pyhtmlgui.replace_element", [self.uid, html_content], skip_results=True)
        else:
            raise Exception("Can't update invisible components")

    def insert_element(self, index: int, element: PyHtmlView) -> bool:
        """
        Insert a new element into DOM at index.
        This is used for example in ObservableDictView and ObservableListView to insert newly created elements.
        """
        html_content = element.render()
        if html_content is not None:  # object might have died, in that case don't render
            self.call_javascript("pyhtmlgui.insert_element", [self.uid, index, html_content], skip_results=True)
            return True
        return False

    def delete(self, remove_from_dom: bool = True) -> None:
        """
        Delete element, detach events, remove from parent, remove from frontend if element is visible

        :param remove_from_dom: If parent element calls delete, remove_from_dom is set to False,
                                because parent removes itself + all childen from dom automatically
        """
        if self.is_visible is True and remove_from_dom is True:
            self.call_javascript("pyhtmlgui.remove_element", [self.uid], skip_results=True)
        self.set_visible(False)
        self.parent._remove_child(self)
        for child in self._children:
            child.delete(remove_from_dom=False)

    def set_visible(self, visible: bool) -> None:
        """
        Set component and childens visibility, components that are not visible get their events detached
        """

        if self.is_visible == visible:
            return

        if visible is False:
            self.is_visible = False
            for observable, target in self._observables:
                try:
                    observable().detach_observer(target())  # resolve weak references
                except Exception:
                    pass
            for child in self._children:
                child.set_visible(False)
        else:
            self.is_visible = True
            for observable, target in self._observables:
                try:
                    observable().attach_observer(target())  # resolve weak references
                except Exception:
                    pass

    def call_javascript(self, js_function_name, args, skip_results=False):
        """
        Call javascript function in frontend.
        :param js_function_name: Name of javascript function
        :param args: Arguments for js function
        :param skip_results: Don't receive results, give some slight performance inprovement because
                             we don't wait for results
        """
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
            raise Exception("Can't javascript_call invisible components")
        return self._instance.call_javascript("pyhtmlgui.eval_script", [script, kwargs], skip_results=skip_results)

    def eval_javascript_electron(self, script, skip_results=False, **kwargs):
        if self.is_visible is False:
            raise Exception("Can't javascript_call invisible components")
        return self._instance.call_javascript("electron.eval_script", [script, kwargs], skip_results=skip_results)

    def _inner_html(self) -> typing.Union[str, None]:
        self._subject = self.subject  # receive hard reference to obj to it does not die on us while rendering
        if self._subject is None:  # Observed object died before render
            return None

        self.set_visible(True)
        for child in self._children:
            child.__was_rendered = False

        try:
            html = self._instance.get_template(self).render({"pyview": self})
        except Exception:
            tb = traceback.format_exc()
            msg = " Exception while rendering Template: %s\n" % self.__class__.__name__
            msg += " %s" % tb.replace("\n", "\n  ").strip()
            self.call_javascript("pyhtmlgui.debug_msg", [msg])
            html = msg
            print(msg)

        # set children that have not been rendered in last pass to invisible
        [c.set_visible(False) for c in self._children if c.__was_rendered is False and c.is_visible is True]

        self.__was_rendered = True
        self._subject = None  # remove hard reference to subject, it may die now
        return html

    def _add_child(self, child: PyHtmlView) -> None:
        self._children.add(child)

    def _remove_child(self, child: PyHtmlView) -> None:
        self._children.remove(child)

    def add_observable(self, subject: Observable, target_function: typing.Callable = None) -> None:
        try:
            if not callable(subject.attach_observer) or not callable(subject.detach_observer):
                raise Exception("object type '%s' can not be observed" % type(subject))
        except Exception:
            raise Exception("object type '%s' can not be observed" % type(subject))
        if target_function is None:
            target_function = self._on_subject_updated

        if type(subject) != weakref.ref:
            subject = weakref.ref(subject)
        if type(target_function) != weakref.WeakMethod:
            target_function = weakref.WeakMethod(target_function)
        self._observables.append([subject, target_function])

    def remove_observable(self, subject: Observable, target_function: typing.Callable = None) -> None:
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
