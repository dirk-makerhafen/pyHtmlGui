from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyhtmlgui.lib.observableDict import ObservableDict
from .pyhtmlview import PyHtmlView
import typing
from threading import Lock


class ObservableDictView(PyHtmlView):
    TEMPLATE_STR = '''
        {% for item in pyview.get_items() %}
            {{ item.render()}}
        {% endfor %}
    '''

    def __init__(self,
                 subject        : ObservableDict,
                 parent         : PyHtmlView,
                 item_class     : type[PyHtmlView],
                 dom_element    : str             = PyHtmlView.DOM_ELEMENT,
                 sort_key       : typing.Callable = None,
                 sort_reverse   : bool            = False,
                 **kwargs):

        self._item_class = item_class
        self.DOM_ELEMENT = dom_element
        self._kwargs = kwargs
        self._wrapped_data = {}
        self._wrapped_data_lock = Lock()
        self.sort_key = sort_key
        self.sort_reverse = sort_reverse
        super().__init__(subject, parent)

    def set_visible(self, visible: bool) -> None:
        if self.is_visible == visible:  # not changed
            return
        self._wrapped_data_lock.acquire()
        super().set_visible(visible)
        self._wrapped_data = {}
        if self.is_visible is True:
            # is we were invisible, we might have missed add/delete events, so recreate our data wrapper
            for key, item in self.subject.items():
                self._wrapped_data[key] = self._create_item(item, key)
        self._wrapped_data_lock.release()

    def get_items(self) -> list:
        items = [item for key, item in self._wrapped_data.items()]
        if self.sort_key is None:
            return sorted(items, key=lambda x: x.item_key)
        else:
            return sorted(items, key=self.sort_key, reverse=self.sort_reverse)

    def _create_item(self, item, key):
        obj = self._item_class(item, self, **self._kwargs)
        obj.item_key = key
        return obj

    def _on_subject_updated(self, source, **kwargs) -> None:
        try:
            self._wrapped_data_lock.acquire()

            if kwargs["action"] == "setitem":
                if kwargs["key"] in self._wrapped_data:
                    self._wrapped_data[kwargs["key"]].delete()  # unrender
                obj = self._create_item(kwargs["item"], kwargs["key"])
                self._wrapped_data[kwargs["key"]] = obj
                index = list(self._wrapped_data.keys()).index(kwargs["key"])
                if self.insert_element(index, obj) is False:
                    del self._wrapped_data[kwargs["key"]]

            if kwargs["action"] == "update":
                for kv in kwargs["items"]:
                    key, item = kv
                    obj = self._create_item(item, kwargs["key"])
                    if key in self._wrapped_data:
                        self._wrapped_data[key].delete()  # unrender
                    self._wrapped_data[key] = obj
                    index = list(self._wrapped_data.keys()).index(kwargs["key"])
                    if self.insert_element(index, obj) is False:
                        del self._wrapped_data[kwargs["key"]]

            if kwargs["action"] in ["delitem", "pop", "popitem"]:
                self._wrapped_data[kwargs["key"]].delete()
                del self._wrapped_data[kwargs["key"]]

            if kwargs["action"] == "clear":
                for key, item in self._wrapped_data.items():
                    item.delete()
                self._wrapped_data.clear()
                self.update()

        finally:
            self._wrapped_data_lock.release()
