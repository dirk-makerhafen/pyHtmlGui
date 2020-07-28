import random
from pyHtmlGui import pyHtmlGuiComponent
try:
    from backend import Example1, Example2, Example3, BackendAppMain
except:
    from .backend import Example1, Example2, Example3, BackendAppMain


# The main class of our example app
class FrontendApp(pyHtmlGuiComponent):

    TEMPLATE_FILE = "main_container.html"

    def __init__(self, observedObject, parentComponent):
        """
        :type observedObject: BackendAppMain
        :type parentComponent: None
        """
        super(FrontendApp, self).__init__(observedObject=observedObject, parentComponent=parentComponent)
        self.example1 = Example1Component(observedObject.example1, parentComponent=self)
        self.example2 = Example2Component(observedObject.example2, parentComponent=self)
        self.example3 = Example3Component(observedObject.example3, parentComponent=self)


class Example1Component(pyHtmlGuiComponent):

    TEMPLATE_STR = '''<p> Current Timestamp: {{this.observedObject.current_timestamp}} <p>'''

    def __init__(self, observedObject, parentComponent):
        """
        :type observedObject: Example1
        :type parentComponent: FrontendApp
        """
        super(Example1Component, self).__init__(observedObject=observedObject, parentComponent=parentComponent)

# A backend python method called from a frontend button, receiving a frontend  field
class Example2Component(pyHtmlGuiComponent):

    TEMPLATE_STR = '''<p> {{this.observedObject.add_two_numbers_last_result}} </p>'''

    def __init__(self, observedObject, parentComponent):
        """
        :type observedObject: Example2
        :type parentComponent: FrontendApp
        """
        super(Example2Component, self).__init__(observedObject=observedObject, parentComponent=parentComponent)


# Some backend process calling a frontend JS function from time to time
class Example3Component(pyHtmlGuiComponent):
    TEMPLATE_STR = '''
       <script>
        function toggle(){
            $("#toggle_field").toggle();
        }
       <script>
       <p id="toggle_field">Here</p> 
    '''

    def __init__(self, observedObject, parentComponent):
        """
        :type observedObject: Example3
        :type parentComponent: FrontendApp
        """
        super(Example3Component, self).__init__(observedObject=observedObject, parentComponent=parentComponent)


