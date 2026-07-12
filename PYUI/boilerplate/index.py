from PYUI.Package.PYUI import PYUI,Element,Component,cpath

'''
Element: OPP facade over procedural PYUI
Component: Add and remove dynamic components from UI
cpath: helps is easy resolving component ids you need not write "component_id_element_id" better use cpath(component_id,element_id)
both are equivalent.
'''

class App:

    def __init__(self,obj:PYUI):

        '''
        Entry point of App class.
        Use this class to work with DOM UI
        '''
        self.pyui = obj


def entry(obj:PYUI):
    
    """
    This is the entry point for your form index.xml
    You can write procedural code using this entrypoint by deleting OPP function. Or use the boilerplate App class
    You can rename the Class to anything
    """
    App(obj) # executing the app class