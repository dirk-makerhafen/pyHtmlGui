from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pyhtmlgui.lib.observableList import ObservableList
import types
import typing
from threading import Lock
from .pyhtmlview import PyHtmlView


class ObservableListView(PyHtmlView):
    TEMPLATE_STR = '''
        {% for item in pyview.get_items() %}
            {{ item.render()}}
        {% endfor %}
    '''

    def __init__(self,
                 subject        : ObservableList,
                 parent         : PyHtmlView,
                 item_class     : type[PyHtmlView],
                 dom_element    : str             = PyHtmlView.DOM_ELEMENT,
                 sort_key       : typing.Callable = None,
                 sort_reverse   : bool            = False,
                 filter_function: typing.Callable = None,
                 **kwargs):

        self._item_class = item_class
        self.DOM_ELEMENT = dom_element
        self._kwargs = kwargs
        self._wrapped_data = []
        self._wrapped_data_lock = Lock()
        self.sort_key = sort_key
        self.sort_reverse = sort_reverse
        self.filter_function = filter_function
        if self.filter_function is None:
            self.filter_function = lambda x: False
        super().__init__(subject, parent)

    def get_items(self) -> list:
        data = [w for w in self._wrapped_data if self.filter_function(w) is False]
        if self.sort_key is None:
            return data
        else:
            return sorted(data, key=self.sort_key, reverse=self.sort_reverse)

    def set_visible(self, visible: bool) -> None:
        if self.is_visible == visible:  # not changed
            return
        self._wrapped_data_lock.acquire()
        super().set_visible(visible)
        self._wrapped_data = []
        if self.is_visible is True:  # was set to invisible
            for item in self.subject:
                self._wrapped_data.append(self._create_item(item))
        self._wrapped_data_lock.release()

    def _create_item(self, item):
        obj = self._item_class(item, self, **self._kwargs)
        obj.loop_index = types.MethodType(lambda x: x.parent.get_element_index(x), obj)
        obj.loop_index_used = False
        return obj

    def _on_subject_updated(self, source, **kwargs):
        try:
            self._wrapped_data_lock.acquire()

            if kwargs["action"] in ["append", "insert"]:
                obj = self._create_item(kwargs["item"])
                self._wrapped_data.insert(kwargs["index"], obj)
                if self.filter_function(obj) is False:
                    if self.insert_element(kwargs["index"], obj) is False:
                        self._wrapped_data.remove(obj)
                    else:  # update items that use the loop index
                        for item in self._wrapped_data[kwargs["index"] + 1:]:
                            if item.loop_index_used is True:
                                item.update()

            if kwargs["action"] == "setitem":
                self._wrapped_data[kwargs["index"]].delete()  # unrender
                obj = self._create_item(kwargs["new_item"])
                self._wrapped_data[kwargs["index"]] = obj
                if self.filter_function(obj) is False:
                    if self.insert_element(kwargs["index"], obj) is False:
                        self._wrapped_data.remove(obj)

            if kwargs["action"] == "extend":
                current_index = kwargs["index"]
                for item in kwargs["items"]:
                    obj = self._create_item(item)
                    self._wrapped_data.insert(current_index, obj)
                    if self.filter_function(obj) is False:
                        if self.insert_element(kwargs["index"], obj) is False:
                            self._wrapped_data.remove(obj)
                        else:
                            current_index += 1
                [item.update() for item in self._wrapped_data[current_index:] if item.loop_index_used is True]

            if kwargs["action"] in ["remove", "pop", "delitem"]:
                self._wrapped_data[kwargs["index"]].delete()
                del self._wrapped_data[kwargs["index"]]
                [item.update() for item in self._wrapped_data[kwargs["index"]:] if item.loop_index_used is True]

            if kwargs["action"] == "sort":
                self.update()
            if kwargs["action"] == "reverse":
                self.update()
        finally:
            self._wrapped_data_lock.release()

    def get_element_index(self, element):
        element.loop_index_used = True
        return self._wrapped_data.index(element)
