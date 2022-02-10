import typing
from datetime import datetime
from pyhtmlgui import PyHtmlView


class AppView(PyHtmlView):
    TEMPLATE_FILE = "appView.html"
    def __init__(self, subject, parent, **kwargs):
        super().__init__(subject, parent, **kwargs)
        singleCounterView = SingleCounterView()
