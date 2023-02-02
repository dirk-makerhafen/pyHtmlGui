from pyhtmlgui import PyHtmlView


class TwoCountersView(PyHtmlView):
    TEMPLATE_STR = '''
        <h4>Two Counters in Sub pages</h4>
        <div class="row">
            <div class="col-md-3">
                <h5>Sidebar</h5>
                <button onclick="pyview.show_page(0)" {% if pyview.current_page == pyview.pages.0 %} style="color:green" {% endif %}>Page 1</button> <br>
                <button onclick="pyview.show_page(1)" {% if pyview.current_page == pyview.pages.1 %} style="color:green" {% endif %}>Page 2</button>
            </div>
            <div class="col-md-8">
                {{ pyview.current_page.render() }} 
            </div>            
        </div>
    '''

    def __init__(self, subject, parent, **kwargs):
        super().__init__(subject, parent, **kwargs)
        self.pages = [
            CounterPageView(subject.counter1, self, "My Counter Name"),
            CounterPageView(subject.counter2, self, "Some Other Name")
        ]
        self.current_page = self.pages[0]

    def show_page(self, page_nr):
        if self.current_page != self.pages[page_nr]:
            self.current_page = self.pages[page_nr]
            self.update()


class CounterPageView(PyHtmlView):
    TEMPLATE_STR = '''
        <h4>Page: {{ pyview.name }}</h4> <br>
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
