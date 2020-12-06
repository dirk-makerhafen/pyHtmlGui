import time
import threading
from pyhtmlgui import PyHtmlGui, PyHtmlView, Observable

class AppView(PyHtmlView):
    TEMPLATE_STR = '''
        i am a item that is updated when the observed backend object changes, this is the normal default way of usage  <br>
        {{ this.observedObject.value}}<br>
         <button onclick='pyhtmlgui.call(this.observedObject.pause_restart);'> {% if this.observedObject.paused == True %} Start {% else %} Pause {% endif %}</button>
    '''
