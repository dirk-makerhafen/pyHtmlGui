import types
from threading import Lock
from .pyhtmlview import PyHtmlView


class ObservableListView(PyHtmlView):
    TEMPLATE_STR = '''
        {% for item in this.get_items() %}
            {{ item.render()}}
        {% endfor %}
    '''

    def __init__(self, observedObject, parentView, item_class, wrapper_element=PyHtmlView.WRAPPER_ELEMENT,
                 sort_lambda=None, sort_reverse=False, filter=None, **kwargs):
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
            return sorted(data, key=self.sort_lambda, reverse=self.sort_reverse)

    def set_visible(self, visible):
        if self.is_visible == visible:  # not changed
            return
        self._wrapped_data_lock.acquire()
        super().set_visible(visible)
        self._wrapped_data = []
        if self.is_visible is True:  # was set to invisible
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
                    if self.insert_element(kwargs["index"], obj) is False:
                        self._wrapped_data.remove(obj)
                    else:
                        [item.update() for item in self._wrapped_data[kwargs["index"] + 1:] if
                         item.loop_index_used == True]  # update items that use the loop index

            if kwargs["action"] == "setitem":
                self._wrapped_data[kwargs["index"]].delete()  # unrender
                obj = self._create_item(kwargs["newItem"])
                self._wrapped_data[kwargs["index"]] = obj
                if self.filter(obj) is False:
                    if self.insert_element(kwargs["index"], obj) is False:
                        self._wrapped_data.remove(obj)

            if kwargs["action"] == "extend":
                current_index = kwargs["index"]
                for item in kwargs["items"]:
                    obj = self._create_item(item)
                    self._wrapped_data.insert(current_index, obj)
                    if self.filter(obj) is False:
                        if self.insert_element(kwargs["index"], obj) is False:
                            self._wrapped_data.remove(obj)
                        else:
                            current_index += 1
                [item.update() for item in self._wrapped_data[current_index:] if item.loop_index_used == True]

            if kwargs["action"] in ["remove", "pop", "delitem"]:
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
