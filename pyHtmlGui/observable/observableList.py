from .observable import Observable

class ObservableList(list, Observable):
    def __init__(self):
        super().__init__()
        Observable.__init__(self)
