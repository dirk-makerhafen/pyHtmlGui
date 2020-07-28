from .observable import Observable

class ObservableDict(dict, Observable):
    def __init__(self):
        super().__init__()
        Observable.__init__(self)
