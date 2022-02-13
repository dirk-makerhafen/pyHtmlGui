from pyhtmlgui import PyHtmlView


class TwoCountersView(PyHtmlView):
    TEMPLATE_FILE = "twoCountersView.html"

    def __init__(self, subject, parent, **kwargs):
        super().__init__(subject, parent, **kwargs)
        self.counter1View = CounterPageView(subject.counter1, self, "Counter 1")
        self.counter2View = CounterPageView(subject.counter2, self, "Counter 2")
        self.current_counter = self.counter1View

    def show_page_1(self):
        if self.current_counter != self.counter1View:
            self.current_counter = self.counter1View
            self.update()

    def show_page_2(self):
        if self.current_counter != self.counter2View:
            self.current_counter = self.counter2View
            self.update()


class CounterPageView(PyHtmlView):
    TEMPLATE_STR = '''
        <h5>Page: {{ pyview.name }}</h5> <br>
        Value: {{ pyview.subject.value }} <br>
        Page update counter: {{ pyview.event_count }}  <br>  
    '''

    def __init__(self, subject, parent, name, **kwargs):
        super().__init__(subject, parent)
        self.name = name
        self.event_count = 0
        self.add_observable(subject, self.update_event_count)

    def update_event_count(self, *args, **kwargs) -> None:
        self.event_count += 1
