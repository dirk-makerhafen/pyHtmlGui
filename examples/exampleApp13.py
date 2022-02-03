import sys
import time
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class App(Observable):
    def on_frontend_ready(self, pyHtmlGuiInstance, nr_of_active_frontends):
        print("on_frontend_ready", pyHtmlGuiInstance, nr_of_active_frontends )

    def on_frontend_exit(self, pyHtmlGuiInstance, nr_of_active_frontends):
        print("frontend_disconnected", pyHtmlGuiInstance, nr_of_active_frontends )
        if nr_of_active_frontends == 0:
            exit(0)


class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        <p>i am a button calling a method of the python frontend object</p> 
        \pyhtmlgui.call(this.foobar)
        \pyhtmlgui.call(this.function, "arg1") 
        I call a python function with arguments and show its return value
        <button onclick="pyhtmlgui.call(this.get_time).then(function(e){alert(e);})">Click me</button>  
        javascript button click -> 
           python function 
        <- return 
           
        I call a python function with arguments 
         The python function calls a javascript function in the frontend and gets its return value via a blocking call and retures it to the caller
         javascript button click -> 
           python function -> 
             javascript function in frontend 
           <- return
         <- return  
         
        I call a python function with arguments 
         The python function calls a javascript function in the frontend and gets its return value via callback
         The callback updates the frontend via eval_javascript, and ignored its return value
         
        I call a python function with arguments 
         The python function calls a javascript function in the ELECTRON main.js publicFunctions class and returns its value 
         
        <button onclick="pyhtmlgui.call(this.clicked)">Click me</button>   
        <button onclick="pyhtmlgui.call(this.exit)">Exit App</button>   
    '''
    def get_time(self):
        return time.time()

    def clicked(self):
        self.call_javascript("create_random_string", ["my prefix"])

        #result = self.call_javascript("create_random_string", ["my prefix"])()

        self.call_javascript("create_random_string", ["my prefix"])(lambda x:print(x))

        self.call_javascript("pyhtmlgui.eval_script", [ "console.log(args.item); return args.item + 'bar';", {"item": "foo"}] )
        self.eval_javascript("console.log(args.item); return args.item + 'bar';", item="foo" )

        self.call_javascript("electron.eval_script", ["console.log(args.item); return args.item + 'bar';", {"item": "foo"}])
        self.eval_javascript_electron("console.log(args.item); return args.item + 'bar';", item="foo")

    def exit(self):
        self.call_javascript("electron.exit", [], skip_results=True)


if __name__ == "__main__":
    electron_exe = sys.argv[1]
    app = App()
    gui = PyHtmlGui(
        app_instance= app,
        view_class= AppView,
        mode          = "electron",
        template_dir  = "templates",
        static_dir    = "static",
        main_html     = "window.html",
        executable    = electron_exe,
        shared_secret = "shared_secret_replace_me", # must be the same in electron pyhtmlgui.json,
        on_frontend_ready = app.on_frontend_ready,
        on_frontend_exit  = app.on_frontend_exit,

    )
    gui.start(show_frontend=True, block=True)
