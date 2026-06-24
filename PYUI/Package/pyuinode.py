class PyUILayoutNode:
    """A completely static, post-validated node. Safe to save to disk."""
    def __init__(self, tag: str, inner_text: str = ""):
        self.tag = tag
        self.innerText = inner_text
        self._attributes = {}
        
        # Explicit slots for common attributes to avoid dictionary overhead later
        self.id = None
        self.style_class = None
        self.style_class_arr = {}
        
        #Callbacks and the hooks are stored here
        self.managed = True # Unmanaged nodes are outside the dom tree and needs to be explicitly managed
        self.callbacks = {} #Exact callback strings are stored here. the PYUI handles the cleanup
          
        
        # Style dictionary to be populated directly on the node later
        self.style = {}
        
        self.firstChild = None
        self.nextSibling = None

    def attributes(self) -> dict:
        return self._attributes
    
    def get(self,attribute):
        return self._attributes[attribute]
    def set(self,attribute,value):
        self._attributes[attribute] = value
        
    def __repr__(self):
        return f"<{self.tag} id='{self.id}'>"