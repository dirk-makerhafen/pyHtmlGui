from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable, ObservableDict, ObservableDictView


class DictItem(Observable):
    def __init__(self, name):
        super().__init__()
        self.name = name
    def setName(self, name):
        self.name = name
        self.notifyObservers()

class App(Observable):
    def __init__(self):
        super().__init__()
        self.my_dict = ObservableDict() # instead of {}
    def set_item(self, key, name):
        self.my_dict[key] = DictItem(name)
    def delete(self, key):
        del self.my_dict[key]
    def rename(self, key, new_name):
        self.my_dict[key].setName(new_name)


class DictItemView(PyHtmlView):
    TEMPLATE_STR = '''
        Item: key:"{{this.item_key}}" {{ this.observedObject.name }} 
        <button onclick='pyhtmlgui.call(this.parentView.parentView.observedObject.delete, {{this.item_key}});'>Delete</button> <br>
        <!--- this.parentView is ObservableListView-->
        <!--- this.parentView.parentView is MainView-->
    '''

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        i am a dict of items rendered via the ObservableDictView helper
        <br> 
        <div> {{ this.dictview.render() }} <div>
        <br> <br> 
        <div>
            Key   <input id="key" type="text"/>
            Value <input id="value" type="text"/>
            <button onclick='pyhtmlgui.call(this.observedObject.set_item, document.getElementById("key").value, document.getElementById("value").value);'>Set Item</button>   
        </div>
        <div>
            Key     <input id="rekey" type="text"/>
            NewName <input id="rename" type="text"/>
            <button onclick='pyhtmlgui.call(this.observedObject.rename, document.getElementById("rekey").value, document.getElementById("rename").value);'>Rename</button>   
        </div>
    '''

    def __init__(self, observedObject, parentView):
        super().__init__(observedObject, parentView)
        self.dictview = ObservableDictView(observedObject=observedObject.my_dict, parentView=self, item_class=DictItemView)


if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance  = App(),
        appViewClass = AppView,
    )
    gui.start(show_frontend=True, block=True)
