from pyhtmlgui import PyHtmlView


class TwoCountersView(PyHtmlView):
    TEMPLATE_FILE = "twoCountersView.html"
    TEMPLATE_STR = '''
        <h4>Two Counters in Sub pages</h4>
        <div class="row">
            <div class="col-md-3">
                <h3>Sidebar</h3>
                <button onclick="pyview.show_page(1)" {% if pyview.current_page == pyview.counter1View %} disabled {% endif %}>Page Counter 1</button> <br>
                <button onclick="pyview.show_page(2)" {% if pyview.current_page == pyview.counter2View %} disabled {% endif %}>Page Counter 2</button>
            </div>
            <div class="col-md-8">
                {{ pyview.current_counter.render() }} 
            </div>            
        </div>
    '''

    def __init__(self, subject, parent, **kwargs):
        super().__init__(subject, parent, **kwargs)
        self.counter1View = CounterPageView(subject.counter1, self, "Counter 1")
        self.counter2View = CounterPageView(subject.counter2, self, "Counter 2")
        self.pages = [self.counter1View, self.counter2View]
        self.current_page = self.counter1View

    def show_page(self, page_nr):
        if self.current_page != self.pages[int(page_nr)]:
            self.current_page = self.pages[int(page_nr)]
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
