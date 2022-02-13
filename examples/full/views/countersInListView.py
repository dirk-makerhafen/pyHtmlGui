from pyhtmlgui import PyHtmlView, ObservableListView


class CountersInListView(PyHtmlView):
    TEMPLATE_FILE = "countersInListView.html"

    def __init__(self, subject, parent, **kwargs):
        super().__init__(subject, parent, **kwargs)
        self.listView = ObservableListView(subject.counters, self, CounterListItemView, wrapper_element="tbody")

    def remove_counter(self, counter_id):
        self.subject.remove_counter(counter_id)


class CounterListItemView(PyHtmlView):
    WRAPPER_ELEMENT = "tr"
    TEMPLATE_STR = '''
    <td>{{pyview.subject.value}}</td>
    <td>
        <button {% if pyview.subject.active == true %}disabled{% endif %} onclick='pyview.subject.start();'>Start</button>
        <button {% if pyview.subject.active == false%}disabled{% endif %} onclick='pyview.subject.stop();'>Stop</button> 
        <button onclick='pyview.subject.reset();'>Reset</button> 
        <button onclick='pyview.parent.parent.remove_counter({{pyview.loop_index()}});'>Delete</button>
    </td>
    '''
