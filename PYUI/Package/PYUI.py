'''
Standard libary for all PYUI contol
'''

from PYUI.pyuinode import PyUILayoutNode
import queue
import uuid
import webview
import traceback
import time
import itertools
import threading
from functools import wraps
import pickle
import os
import warnings
from PYUI.settings import  CompilerSettings
import json
import sys

class InvalidPropError(Exception):
    pass

SysCall = {
    'START':0,
    'END':1,
    'BATCH_UPDATE':2,
    'STOP_HOOKS':3,
    'REGISTER_SYSCALL_CALLBACK':4,
    'UNREGISTER_SYSCALL_CALLBACK':5,
    'SEND_SYSCALL':6,
    'EXECUTE_JS':7,
    'REGISTER_CALLBACK':8,
    'UNREGISTER_CALLBACK':9,
    'NEW_FORM_LAUNCH':10,
    'CONTENT_GRAB':11,
    'POLL':12,
}

CALLBACK_QUEUE_LIST = {}
THREAD_CALLBACKS = {}

# Thread-Local Storage to automatically track executing callback context
_thread_context = threading.local()

# ==============================================================================
# 1. GLOBAL FALLBACK COMMIT ENGINE (For Ungrouped Code)
# ==============================================================================
FALLBACK_EXECUTION_QUEUE = queue.Queue()

def processParams(v:str,props:dict):
    if not '{' in v:
        return v #no need to process params without props
    
    iscurlyStarted = False
    iscurlyEnded = False
    buffer = ""
    key = ""
    for n,char in enumerate(v+" "):
        if char == '{':
            if  n == 0:
                iscurlyStarted = True
            elif v[n-1] == "/":

                buffer += char
            elif iscurlyStarted == True:
                #it is just something inside {} just add to buffer
                key += char
            
            elif iscurlyEnded == True and iscurlyStarted == True:
                buffer += char
            else:
                 iscurlyStarted = True


        elif char == "}":

            if n == 0:
                buffer += char
            elif v[n-1] == "/":
                if iscurlyStarted == True:

                    key  += char
                    
                else:
                    buffer += char
     
            elif iscurlyStarted == True:

                iscurlyStarted = False
                iscurlyEnded = False

                try:
                    buffer += props[key.strip()]
                except KeyError:
                    raise InvalidPropError(f'The prop:{key} is used but not explicitly defined in parent layout file add {key}="some_value" to fix it.')
                key = ""
                
        elif char == "/" and (v[n+1] == "{" or v[n+1] == "}"):
            continue
        else:
            if iscurlyStarted == True and iscurlyEnded == False:
                key += char
            else:
                buffer += char

    return buffer.strip()


def resource_path(*parts):
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = ""

    return os.path.join(base, *parts)


def _fallback_sequential_worker():
    """Consumes and processes commits from all ungrouped threads sequentially."""
    while True:
        item = FALLBACK_EXECUTION_QUEUE.get()
        if item == "END":
            break
        
        scope, updates = item
        if scope == globals: 
            scope = globals()
            
        try:
            for key, value in updates.items():
                if isinstance(scope, dict):
                    scope[key] = value  
                else:
                    setattr(scope, key, value)  
        except Exception as e:
            print(f"[Fallback Worker Error] Failed to resolve commit: {e}")

_fallback_thread = threading.Thread(target=_fallback_sequential_worker, daemon=True)
_fallback_thread.start()


# ==============================================================================
# 2. DSU GROUP ENGINE (Serializes both execution and writes for grouped items)
# ==============================================================================
class CallbackDSU:
    def __init__(self):
        self.parent = {}
        self.group_queues = {}  # Maps group root -> queue.Queue

    def find(self, item):
        if item not in self.parent:
            self.parent[item] = item
            return item
        if self.parent[item] == item:
            return item
        self.parent[item] = self.find(self.parent[item])  
        return self.parent[item]

    def union(self, item1, item2):
        root1 = self.find(item1)
        root2 = self.find(item2)
        if root1 != root2:
            self.parent[root2] = root1

    def ensure_worker_exists(self, root_item):
        """Spawns a private sequential worker thread for a specific DSU group."""
        if root_item not in self.group_queues:
            q = queue.Queue()
            self.group_queues[root_item] = q
            
            def group_commit_worker():
                # Flag this thread so nested commits are evaluated synchronously
                _thread_context.is_group_worker = True
                while True:
                    item = q.get()
                    
                    # If the item is an executable job (the full callback lifecycle)
                    if callable(item):
                        try:
                            item()
                        except Exception as e:
                            print(f"[Group Worker Job Error] Execution crashed: {e}")
                    else:
                        # Fallback for state transaction tuples
                        scope, updates = item
                        if scope == globals: 
                            scope = globals()
                        try:
                            for key, value in updates.items():
                                if isinstance(scope, dict):
                                    scope[key] = value
                                else:
                                    setattr(scope, key, value)
                        except Exception as e:
                            print(f"[Group Worker Error] Failed to resolve commit: {e}")
                        
            t = threading.Thread(target=group_commit_worker, daemon=True)
            t.start()
        return self.group_queues[root_item]

dsu = CallbackDSU()

def group(*functions):
    """Binds multiple functions to a shared sequential execution queue."""
    raw_funcs = [f.__func__ if hasattr(f, '__func__') else f for f in functions]
    for i in range(len(raw_funcs) - 1):
        dsu.union(raw_funcs[i], raw_funcs[i+1])

def background(func):
    """Decorator to offload heavy tasks while preserving thread-local tracking context."""
    raw_func = func.__func__ if hasattr(func, '__func__') else func
    
    @wraps(func)  # Preserves __name__, __doc__, and original properties
    def wrapper(*args, **kwargs):
        raw_func = func.__func__ if hasattr(func, '__func__') else func
        def thread_target():
            _thread_context.current_callback = raw_func
            func(*args, **kwargs)
        t = threading.Thread(target=thread_target, daemon=True)
        t.start()
    return wrapper

class Message:
    def __init__(self, syscall, msg=""):
        self.syscall = syscall
        self.msg = msg
        self.uuid = str(uuid.uuid4()).replace("'", "")


def _callback_handler(callback, q: queue.Queue, obj,args:tuple):
    raw_callback = callback.__func__ if hasattr(callback, '__func__') else callback
    
    while True:
        val = q.get()
        if val == "END":
            break
            
        # Check if this callback belongs to a serialized conflict group
        if raw_callback in dsu.parent:
            root = dsu.find(raw_callback)
            group_queue = dsu.ensure_worker_exists(root)
            
            # Wrap the entire lifecycle of the callback into a serializable job unit
            def execution_job():
                try:
                    _thread_context.current_callback = raw_callback
                    callback(obj, val,*args)
                except Exception as ex:
                    print(f"Error in callback execution: {callback.__name__} \n -> Error: {ex}")
                    obj.End()
            
            group_queue.put(execution_job)
            
        else:
            # Ungrouped callback executes instantly on its pre-existing thread loop
            try:
                _thread_context.current_callback = raw_callback
                callback(obj, val,*args)
            except Exception as ex:
                print(f"Error in callback execution: {callback.__name__} \n -> Error: {ex}")
                obj.End()

def camelCaseConverter(txt: str):
    offset = 0
    length = len(txt)
    formatted = ""
    for j in range(length):
        if j + offset >= length:
            break
        char = txt[j + offset]
        if char == "-":
            offset += 1
            if j + offset < length:
                formatted += txt[j + offset].capitalize()
        else:
            formatted += char
    return formatted


class IdNotFoundError(Exception): pass
class ClassChangeActionNotFoundError(Exception): pass
class CallbackNotFoundError(Exception): pass
class CallbackCollisionError(Exception): pass
class StyleClassNotFoundError(Exception): pass
class UnsafeStringInjectionBLocked(Exception): pass
class AttributeNotFoundError(Exception): pass
class SysCallNotFoundError(Exception): pass
class IdCollisionError(Exception): pass
class IllegalManagedNodeDeletionError(Exception): pass

class PYUI:
    def __init__(self,SQ:queue.Queue,MQ:queue.Queue,window,infoDict,syscall,config):
        self.SQ = SQ
        self.__window:webview.Window = window
        self.tree:PyUILayoutNode = infoDict['layout_tree']
        self.id_map = infoDict['id_index_map']
        self.id_windows = infoDict['id_windows']
        self.Syscall = syscall
        self.MQ = MQ
        self.counter = itertools.count()
        self.__user_Syscall = {'_':0}
        self.config:CompilerSettings = config
        
        self.RegisterSyscall('ADD_NODE_END')
        self.RegisterSyscall('REM_NODE')
    

    def commit(self, scope, **updates):
        """
        Declaration engine that funnels state mutations safely into serialization lines.
        Supports '_callback' parameter to target a specific group queue from background tasks.
        """
        # Extract explicit callback context if provided, otherwise check thread local storage
        target_cb = updates.pop('_callback', getattr(_thread_context, 'current_callback', None))

        # If we are already running inside the group worker thread processing a job, 
        # apply the write immediately to preserve expected top-to-bottom procedural updates.
        if getattr(_thread_context, 'is_group_worker', False):
            if scope == globals: 
                scope = globals()
            try:
                for key, value in updates.items():
                    if isinstance(scope, dict):
                        scope[key] = value
                    else:
                        setattr(scope, key, value)
            except Exception as e:
                print(f"[Synchronous Commit Error] Failed to resolve: {e}")
            return

        transaction = (scope, updates)
        
        # Route to the group queue if the context belongs to a DSU group
        if target_cb and target_cb in dsu.parent:
            root = dsu.find(target_cb)
            group_queue = dsu.ensure_worker_exists(root)
            group_queue.put(transaction)
        else:
            FALLBACK_EXECUTION_QUEUE.put(transaction)

    def _startCommunication(self):
        msg = Message(SysCall['START'])
        self.SQ.put((SysCall['START'],next(self.counter),msg))

    def __ExecuteJS(self,argv:dict,type,ret=False):
        json = {"js_type":type,"args":argv}
        msg = Message(SysCall['EXECUTE_JS'],json)
        if not ret:
            self.SQ.put((SysCall['EXECUTE_JS'],next(self.counter),msg))
        return msg
    
    def getAttrib(self,id,attribute):
        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        q = queue.Queue(1)
        msg = Message(SysCall['CONTENT_GRAB'],{"id":id,"attrib":attribute,"queue":q})
        self.SQ.put((SysCall['CONTENT_GRAB'],next(self.counter),msg))
        val = q.get()
        return val

    def getTag(self,id):
        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        node:PyUILayoutNode = self.id_map[id]
        return node.tag
    
    def GetAllAttrib(self,id):
        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        node:PyUILayoutNode = self.id_map[id]
        return node.attributes()
    
    def set(self,id,attribute,value,ret=False):
        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        node:PyUILayoutNode = self.id_map[id]
        node.set(attribute,value)
        return self.__ExecuteJS({"id":id,"att":attribute,"value":value},"update",ret=ret)
    
    def setStyle(self,id,attribute,value,ret=False):
        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        if "\"" in  value or "'" in value:
            raise UnsafeStringInjectionBLocked(f"[Runtime Error Log] The given value is unsafe.")
        node:PyUILayoutNode = self.id_map[id]
        node.style[attribute] = value
        param = camelCaseConverter(attribute)
        return self.__ExecuteJS({"id":id,"att":param,"value":value},'updateStyle',ret=ret)
    
    def changeClass(self,id:str,className:str,action:str,ret=False):
        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        cleaned_action = action.upper().strip()
        if not cleaned_action in ['ADD','TOGGLE','REMOVE']:
            raise ClassChangeActionNotFoundError(f'[Runtime Error Log] Cannot handle action:{action}')
        
        action = action.lower().strip()
        toRet = self.__ExecuteJS({"id":id,"action":action.upper().strip(),"class":className},"addstyleclass",ret=ret)
        node:PyUILayoutNode = self.id_map[id]
        if cleaned_action == 'ADD':
            if not className in node.style_class_arr:
                node.style_class_arr[className] = True
        elif cleaned_action == 'REMOVE':
            if not className in node.style_class_arr:
                raise StyleClassNotFoundError(f'[Runtime Error Log] Class {className} not found.')
            del node.style_class_arr[className]
        elif cleaned_action == 'TOGGLE':
            if not className in node.style_class_arr:
                node.style_class_arr[className] = True
            else:
                del node.style_class_arr[className]
        return toRet
 
    def getClassList(self,id:str):
        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        node:PyUILayoutNode = self.id_map[id]
        return list(node.style_class_arr)

    def setText(self,id,newText,ret=False):
        if id not in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        node:PyUILayoutNode = self.id_map[id]
        node.set("innerText",newText)
        return self.__ExecuteJS({"id":id,"text":newText},'updateText',ret=ret)

    def removeAttrib(self,id,attribute,ret=False):
        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        if not attribute in self.id_map[id]._attributes and attribute != 'style':
            raise AttributeNotFoundError(f"Attribute {attribute} not found.")
        return self.__ExecuteJS({"id":id,"att":attribute},'remove',ret=ret)

    def changeWindow(self,id):
        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] Given ID:{id} is not present.")
        if id not in self.id_windows:
            raise KeyError(f'[Runtime Error Log] The given id:{id} not defined.')
        msgList = []
        for win in self.id_windows:
            if id == win:
                msgList.append(self.removeAttrib(win,'style',ret=True))
            else:
                msgList.append(self.set(win,'style','display:none;',ret=True))
        self.sendBatch(msgList)

    def getPYUIRawNode(self,id)->PyUILayoutNode:
        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        return self.id_map[id]

    def loadForm(self,formName):
        msg = Message(SysCall['NEW_FORM_LAUNCH'],formName)
        self.MQ.put(msg)
        
    def RegisterCallback(self,id:str,typeOfCallback:str,callback,args:tuple=()):

        typeOfCallback = typeOfCallback.strip()


        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        token = id+":"+typeOfCallback
        q = queue.Queue(100)
        if token in CALLBACK_QUEUE_LIST:
            raise CallbackCollisionError("Cannot duplicate event registrations.")
        msg = Message(SysCall['REGISTER_CALLBACK'],{"id":id,"callback_type":typeOfCallback,"callback_queue":q})
        CALLBACK_QUEUE_LIST[token] = {"queue":q,"uuid":msg.uuid}

        f = threading.Thread(target=_callback_handler,args=(callback,q,self,args,))
        f.daemon = True
        f.start()
        THREAD_CALLBACKS[token] = f

        node:PyUILayoutNode = self.id_map[id]
        node.callbacks[(id,typeOfCallback)] = True
        self.SQ.put((SysCall['REGISTER_CALLBACK'],next(self.counter),msg))

    def UnRegisterCallBack(self,id:str,typeOfCallback:str):

        typeOfCallback = typeOfCallback.strip()

        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        token = id+":"+typeOfCallback
        if not token in CALLBACK_QUEUE_LIST:
            raise CallbackNotFoundError("Cannot remove non-existent event.")
        dat = CALLBACK_QUEUE_LIST[token]
        m = Message(SysCall['UNREGISTER_CALLBACK'],dat["uuid"])
        self.SQ.put((SysCall['UNREGISTER_CALLBACK'],next(self.counter),m))
        q:queue.Queue = CALLBACK_QUEUE_LIST[token]['queue']     
        q.put("END") 
        node:PyUILayoutNode = self.id_map[id]
        del node.callbacks[(id,typeOfCallback)]
        del CALLBACK_QUEUE_LIST[token]

    def ReRegisterCallback(self,id,typeOfCallback,callback,args:tuple=()):

        self.UnRegisterCallBack(id,typeOfCallback)
        self.RegisterCallback(id,typeOfCallback,callback,args)
        
    def End(self):
        msg = Message(SysCall['END'])
        self.SQ.put((SysCall['END'],next(self.counter),msg))

    def RegisterSyscall(self,syscall_name):
        if not syscall_name in self.__user_Syscall:
            self.__user_Syscall[syscall_name] = True

    def RemoveSyscall(self,syscall_name):
        if syscall_name in self.__user_Syscall:
            del self.__user_Syscall[syscall_name]
            if syscall_name in CALLBACK_QUEUE_LIST:
                m = Message(SysCall['UNREGISTER_SYSCALL_CALLBACK'],'')
                self.SQ.put((SysCall['UNREGISTER_SYSCALL_CALLBACK'],next(self.counter),m))
                q:queue.Queue = CALLBACK_QUEUE_LIST[syscall_name]['queue']     
                q.put("END") 
                del CALLBACK_QUEUE_LIST[syscall_name]
        else:
            raise SysCallNotFoundError(f'Syscall not found: {syscall_name}')
    
    def RegisterSyscallCallback(self,syscall_name,callback,args:tuple=()):
        q = queue.Queue(100)
        if syscall_name in CALLBACK_QUEUE_LIST:
            raise CallbackCollisionError("Syscall collision.")
        msg = Message(SysCall['REGISTER_SYSCALL_CALLBACK'],{"callback_queue":q,'name':syscall_name})
        self.SQ.put((SysCall['REGISTER_SYSCALL_CALLBACK'],next(self.counter),msg))
        CALLBACK_QUEUE_LIST[syscall_name] = {"queue":q,"uuid":msg.uuid}
        f = threading.Thread(target=_callback_handler,args=(callback,q,self,args,))
        f.daemon = True
        f.start()
        THREAD_CALLBACKS[syscall_name] = f

    def UnSyscallRegisterCallBack(self,syscall_name):
        if not syscall_name in self.__user_Syscall:
            raise SysCallNotFoundError(f'Syscall {syscall_name} not found.')
        m = Message(SysCall['UNREGISTER_SYSCALL_CALLBACK'],{'name':syscall_name})
        self.SQ.put((SysCall['UNREGISTER_SYSCALL_CALLBACK'],next(self.counter),m))
        q:queue.Queue = CALLBACK_QUEUE_LIST[syscall_name]['queue']     
        q.put("END") 
        del CALLBACK_QUEUE_LIST[syscall_name]
     
    def sendSyscall(self,syscall_name,msg):
        if not syscall_name in self.__user_Syscall:
            raise SysCallNotFoundError(f'Syscall {syscall_name} not found.')
        m = Message(SysCall['SEND_SYSCALL'],{"msg":msg,'type':syscall_name})
        self.SQ.put((SysCall['SEND_SYSCALL'],next(self.counter),m))

    def sendBatch(self,batch:list[Message]):
        m = Message(SysCall['BATCH_UPDATE'],batch)
        self.SQ.put((SysCall['BATCH_UPDATE'],next(self.counter),m))
        
    def RegisterUnmanagedNode(self,id:str,tag:str):
        if id in self.id_map:
            raise IdCollisionError(f'ID {id} already exists.')
        node = PyUILayoutNode(tag)
        node.managed = False
        self.id_map[id] = node

    def UnRegisterUnmangedNode(self,id:str):
        if id not in self.id_map:
            raise IdNotFoundError(f'ID {id} does not exist.')
        node:PyUILayoutNode = self.id_map[id]
        if node.managed == True:
            raise IllegalManagedNodeDeletionError(f'Managed node ID {id} cannot be unregistered.')
        for idofcallback,typeofCallback in node.callbacks:
            self.UnRegisterCallBack(idofcallback,typeofCallback)
        del self.id_map[id]

    def setWindowTitle(self,title:str):
        self.__window.set_title(title)
    def SetisOnTop(self,isontop):
        self.__window.on_top = isontop
    def GetisOnTop(self) -> bool:
        return self.__window.on_top 
    def getX(self) -> int:
        return self.__window.x
    def getY(self) ->int:
        return self.__window.y
    def getResolution(self) -> dict:
        return self.__window.width,self.__window.height
    def Hide(self):
        self.__window.hide()
    def Show(self):
        self.__window.show()

class Component:

    def __init__(self,obj:PYUI,componentName:str):
        '''
        To load a component
        '''
        self.component_name = componentName.strip()+'.bin'
        self.pyui_instance = obj

        self.load = pickle.load(
            open(
            os.path.join('compiled_components',componentName.strip()+'.bin')
            ,'rb')
            )
        self.tree = self.load['layout_tree']
        self.idList = self.load['id_index_map']

        self.component_list = {}

        

    def __convert_node_to_html(self,node,HTML_TAG_CONVERSION_MAP:dict,LAYOUT_CONTAINER_TAGS:dict,props_dict:dict,prefix_name:str='') -> str:
        if not node:
            return ""

        # CRITICAL: Always enforce lower-casing immediately at entry point
        tag_lower = node.tag.lower().strip()

        if tag_lower == 'componentfile':
            tag_lower = node.tag.strip()


        #IMPORTANT:No styles tag after main-content.if found it will trigger warning
        if tag_lower == "style":
            warnings.warn("Styles inside and below main-content are not evaluated.Please link them out of main content and 'above it'",SyntaxWarning)

        html_tag = HTML_TAG_CONVERSION_MAP.get(tag_lower, tag_lower)

        attr_parts = []
        inner_text = "" 

        element_id = getattr(node, 'id', None)
        if element_id:
            if prefix_name.strip() != '':
                attr_parts.append(f'id="{prefix_name+'_'+element_id}"')
            else:
                attr_parts.append(f'id="{element_id}"')


        # Process attributes smoothly
        for k, v in node.attributes().items():
            k_lower = k.lower().strip()

            if k_lower == "id":
                continue

            v = processParams(v,props_dict)

            if k_lower == "innertext":
                inner_text = v
            elif k_lower == "style-class":
                attr_parts.append(f'class="{v}"')
            else:
                attr_parts.append(f'{k}="{v}"')

        if tag_lower == "window":
            raise RuntimeError('windows are not allowed inside components')

        attr_str = " " + " ".join(attr_parts) if attr_parts else ""

        # CASE A: Leaf Widgets - Close immediately
        if tag_lower not in LAYOUT_CONTAINER_TAGS:
            return f"<{html_tag}{attr_str}>{inner_text}</{html_tag}>\n"

        # CASE B: Layout Containers - Process internal tree nodes explicitly before closing
        child_content = ""
        current_child = node.firstChild
        while current_child:
            child_content += self.__convert_node_to_html(current_child,LAYOUT_CONTAINER_TAGS=LAYOUT_CONTAINER_TAGS,HTML_TAG_CONVERSION_MAP=HTML_TAG_CONVERSION_MAP,props_dict=props_dict,prefix_name=prefix_name)
            current_child = current_child.nextSibling

        # Children are now safely locked inside the parent tag container!
        return f"<{html_tag}{attr_str}>\n{child_content}</{html_tag}>\n"
    
    def __addComponent(self,parentID:str,mode,**props):

        if mode == 'after':
            if parentID not in self.component_list:
                raise IdNotFoundError(f'Given component id:{parentID} is not found.')

        else:
            if parentID not in self.pyui_instance.id_map:
                raise IdNotFoundError(f'Given parent id:{parentID} is not found.')

        unique_id = uuid.uuid4().hex
        
        string_html = self.__convert_node_to_html(
            self.tree,
            self.pyui_instance.config.HTML_TAG_CONVERSION_MAP,
            self.pyui_instance.config.LAYOUT_CONTAINER_TAGS,
            props,
            unique_id
        )

        string_html = f"<div id={unique_id}>{string_html}</div>"

        self.pyui_instance.RegisterUnmanagedNode(unique_id,'div')
        # registered nodes
        for element_id in self.idList:
            self.pyui_instance.RegisterUnmanagedNode(unique_id+'_'+element_id,self.idList[element_id].tag)


        #send syscall to add the node
        toSend = {'parent_id':parentID,'html_to_add':string_html,"mode":mode}
        self.pyui_instance.sendSyscall('ADD_NODE_END',json.dumps(toSend))

        self.component_list[unique_id] = True

        return unique_id
    
    def appendComponent(self,parentID:str,**props):
        return self.__addComponent(parentID,'append',**props)
    
    def addComponentTop(self,parentID:str,**props):
        return self.__addComponent(parentID,'top',**props)

    def addComponentAfter(self,preceedingID:str,**props):
        return self.__addComponent(preceedingID,'after',**props)
    
    def removeComponent(self,node_id:str):

        if not node_id in self.component_list:
            raise IdNotFoundError(f'The given node id:{node_id} not found or is out of scope of this class.')
        
        toSend = {"id":node_id}
        
        self.pyui_instance.sendSyscall('REM_NODE',json.dumps(toSend))
        

        



class Pipeline:
    def __init__(self):
        self.steps = []
    def add(self, target):
        self.steps.append(target)
    def call(self,args:list[tuple]=[]):
        for target,arg in zip(self.steps,args):
                try: res = target(*arg,ret=True)
                except Exception as ex: yield -1
                yield res

class Hook:
    def __init__(self,pipe:Pipeline,pyui:PYUI,fps:int=30):
        self.tp = 1/fps
        self.obj:PYUI = pyui
        self.pipe = pipe
        self.args = []
        self.q = queue.Queue()
        self.lock = threading.Lock()
        self.dirty = False
        th = threading.Thread(target=self.__hook_handler,args=(self.q,))
        th.daemon = True
        th.start()
        msg = Message(SysCall['STOP_HOOKS'],self.q)
        self.obj.SQ.put((SysCall['STOP_HOOKS'],next(self.obj.counter),msg))
    
    def __hook_handler(self,msg_bus:queue.Queue):
        while True:
            try:
                msg = msg_bus.get_nowait()
                if msg == 'END': break
            except: pass
            if self.dirty:
                with self.lock: args = self.args
                self.flush(args)
                self.dirty = False
                time.sleep(self.tp)
            else: self.sleep()

    def flush(self,arg):
        msgs = []
        for j in self.pipe.call(arg):
            if j == -1: self.obj.End()
            msgs.append(j)
        self.obj.sendBatch(msgs)
    def sleep(self): time.sleep(self.tp)
    def update(self,args:list[tuple]=[]):
        with self.lock:
            self.args = args
            self.dirty = True
    def endHook(self):
        time.sleep(self.tp*2)
        self.q.put('END')