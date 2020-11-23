import sys
sys.path.insert(0, ".")
from pyHtmlGui import PyHtmlGui, PyHtmlView, Observable, ObservableList, ObservableListView

class ListItem(Observable):
    def __init__(self, name):
        super().__init__()
        self.name = name
    def setName(self, name):
        self.name = name
        self.notifyObservers()


class App(Observable):
    def __init__(self):
        super().__init__()
        self.my_list = ObservableList() # instead of []

    def append_item(self, name):
        self.my_list.append(ListItem(name))
    def insert(self, index, name):
        self.my_list.insert(index, ListItem(name))
    def delete(self, index):
        del self.my_list[index]
    def rename(self, index, new_name):
        self.my_list[index].setName(new_name)


class ListItemView(PyHtmlView):
    TEMPLATE_STR = '''
        Item:{{this.loop_index()}}, {{ this.observedObject.name }}  
        <button onclick='pyhtmlgui.call(this.parentView.parentView.observedObject.delete, {{this.loop_index()}});'>Delete</button> <br>
        <!--- this.parentView is ObservableListView-->
        <!--- this.parentView.parentView is MainView-->
    '''


class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        i am a list of items rendered via the ObservableListView helper<br>
        {{ this.listView.render() }}
        <br><br>
        <div>
            Name <input id="name" type="text"/>
            <button onclick='pyhtmlgui.call(this.observedObject.append_item, document.getElementById("name").value);'>Append</button>   
        </div>
        <div>
            Name  <input id="name1" type="text"/>
            Index <input id="index1" type="number"/>
            <button onclick='pyhtmlgui.call(this.observedObject.insert, parseInt(document.getElementById("index1").value), document.getElementById("name1").value);'>Insert</button>   
        </div>
        <div>
            New Name <input id="rename1" type="text"/>
            Index    <input id="reindex1" type="number"/>
            <button onclick='pyhtmlgui.call(this.observedObject.rename, parseInt(document.getElementById("reindex1").value), document.getElementById("rename1").value);'>Rename</button>   
        </div>
    '''
    def __init__(self, observedObject, parentView):
        super().__init__(observedObject, parentView)
        self.listView = ObservableListView(observedObject=observedObject.my_list, parentView=self, item_class=ListItemView)


if __name__ == "__main__":
    gui = PyHtmlGui(
        appInstance  = App(),
        appViewClass = AppView,
    )
    gui.start(show_frontend=True, block=True)
