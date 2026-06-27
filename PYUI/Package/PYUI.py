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
import warnings

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

class Message:
    def __init__(self, syscall, msg=""):
        self.syscall = syscall
        self.msg = msg
        self.uuid = str(uuid.uuid4()).replace("'", "")




def _callback_handler(callback,q:queue.Queue,obj):
    while True:
        val = q.get()
        if val == "END": #break in case STOP signal is recived
            break
        else:
            try:
                callback(obj,val) #execute the function
            except Exception as ex:
                print(f"""Error in callback function:{callback.__name__} \n ->Error:{ex}""")
                print("==========================================================================")
                traceback.print_stack()
                print("==========================================================================")
                obj.End()

def camelCaseConverter(txt: str):
    # convert a attrib to camelCase
    offset = 0
    length = len(txt)
    formatted = ""
    for j in range(length):

        if j + offset >= length:
            break  # we reached the end

        char = txt[j + offset]
        if char == "-":
            offset += 1
            # SAFETY CHECK: Ensure the next index isn't out of bounds
            if j + offset < length:
                formatted += txt[j + offset].capitalize()
        else:
            formatted += char

    return formatted  # Don't forget to return the result!





        

class IdNotFoundError(Exception):
    pass

class ClassChangeActionNotFoundError(Exception):
    pass

class CallbackNotFoundError(Exception):
    pass

class CallbackCollisionError(Exception):
    pass

class StyleClassNotFoundError(Exception):
    pass

class UnsafeStringInjectionBLocked(Exception):
    pass

class AttributeNotFoundError(Exception):
    pass

class SysCallNotFoundError(Exception):
    pass

class IdCollisionError(Exception):
    pass

class IllegalManagedNodeDeletionError(Exception):
    pass

class PYUI:
    def __init__(self,SQ:queue.Queue,MQ:queue.Queue,window,infoDict,syscall):
      
        self.SQ = SQ
        self.__window:webview.Window = window
        self.tree:PyUILayoutNode = infoDict['layout_tree']
        self.id_map = infoDict['id_index_map']
        self.id_windows = infoDict['id_windows']
        self.Syscall = syscall
        self.MQ = MQ
        self.counter = itertools.count()
        self.__user_Syscall = {'_':0}

    def _startCommunication(self):
        #print(f"[PYUI Engine] Sending START. Queue Memory Address: {id(self.SQ)}")
        msg = Message(SysCall['START'])
        self.SQ.put((SysCall['START'],next(self.counter),msg))

    def __ExecuteJS(self,argv:dict,type,ret=False):

        json = {"js_type":type,"args":argv}

        
        msg = Message(SysCall['EXECUTE_JS'],json)
        if not ret:
            self.SQ.put((SysCall['EXECUTE_JS'],next(self.counter),msg))

        return msg
    

    def getAttrib(self,id,attribute):
        # node:PyUILayoutNode = self.id_map[id]
        # return node.get(arribute)
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
            raise UnsafeStringInjectionBLocked(f"[Runtime Error Log] The given value is not a valid css value and is unsafe to use.")
        
        node:PyUILayoutNode = self.id_map[id]

        #add the style to the python vdom
        node.style[attribute] = value

        #we need to convert the attribute to camelcase
        param = camelCaseConverter(attribute)

        return self.__ExecuteJS({"id":id,"att":param,"value":value},'updateStyle',ret=ret)
    
    def changeClass(self,id:str,className:str,action:str,ret=False):

        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        
        cleaned_action = action.upper().strip()
        
        if  not cleaned_action  in ['ADD','TOGGLE','REMOVE']:
            raise ClassChangeActionNotFoundError(f'[Runtime Error Log] Can not handle:{action} for class')

        
        action = action.lower().strip()
        toRet = self.__ExecuteJS({"id":id,"action":action.upper().strip(),"class":className},"addstyleclass",ret=ret)

        #save the changes in the layout tree
        node:PyUILayoutNode = self.id_map[id]

        if cleaned_action == 'ADD':
            if not className in node.style_class_arr:
                node.style_class_arr[className] = True

        elif cleaned_action == 'REMOVE':
            if not className in node.style_class_arr:
                raise StyleClassNotFoundError(f'[Runtime Error Log] The given class {className} is not found for given id {id}')
            
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
            raise AttributeNotFoundError(f"Attribute {attribute} not found for id {id}.")
        
        
        return self.__ExecuteJS({"id":id,"att":attribute},'remove',ret=ret)


    def changeWindow(self,id):

        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] Given ID:{id} is not present in the UI.")
        if id not in self.id_windows:
            raise KeyError(f'[Runtime Error Log] [PYUI] The given id:{id} not defined in Form layout.')
        
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
        
    def RegisterCallback(self,id,typeOfCallback,callback):

        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        
        token = id+":"+typeOfCallback
        q = queue.Queue(100)

        if token in CALLBACK_QUEUE_LIST:
            raise CallbackCollisionError("Can not register another event when already existing event registered.")
        
        msg = Message(SysCall['REGISTER_CALLBACK'],{"id":id,"callback_type":typeOfCallback,"callback_queue":q})

        #th = threading.Thread(target=_callback_handler,args=(callback,q,self,))
        
        #store all the queue and threads in a list....
        CALLBACK_QUEUE_LIST[token] = {"queue":q,"uuid":msg.uuid}

        f = threading.Thread(target=_callback_handler,args=(callback,q,self,))
        f.daemon = True
        f.start()
        THREAD_CALLBACKS[token] = f

        #Register the callback to the callback list
        node:PyUILayoutNode = self.id_map[id]


        node.callbacks[(id,typeOfCallback)] = True

        self.SQ.put((SysCall['REGISTER_CALLBACK'],next(self.counter),msg))


    def UnRegisterCallBack(self,id,typeOfCallback):
        if not id in self.id_map:
            raise IdNotFoundError(f"[Runtime Error Log] The given id:{id} not found.")
        
        token = id+":"+typeOfCallback
        if not token in CALLBACK_QUEUE_LIST:
            raise CallbackNotFoundError("Can not remove a non existing Event....")
        
        dat = CALLBACK_QUEUE_LIST[token]
        m = Message(SysCall['UNREGISTER_CALLBACK'],dat["uuid"])
        self.SQ.put((SysCall['UNREGISTER_CALLBACK'],next(self.counter),m))

        #Stop the callback function cleanly
        q:queue.Queue = CALLBACK_QUEUE_LIST[token]['queue']     
        q.put("END") 


        node:PyUILayoutNode = self.id_map[id]

        del node.callbacks[(id,typeOfCallback)]


        #unregister the queue from the hashmap
        del CALLBACK_QUEUE_LIST[token]
        
    def End(self):
        msg = Message(SysCall['END'])
        self.SQ.put((SysCall['END'],next(self.counter),msg))

    #Function to register syscall

    def RegisterSyscall(self,syscall_name):
        
        if not syscall_name in self.__user_Syscall:
            self.__user_Syscall[syscall_name] = True
            print(self.__user_Syscall)

    def RemoveSyscall(self,syscall_name):
        if syscall_name in self.__user_Syscall:
            print("[Debug] Found syscall")
            del self.__user_Syscall[syscall_name]
            print("[Debug] Syscall deleted")

            if syscall_name in CALLBACK_QUEUE_LIST:
                m = Message(SysCall['UNREGISTER_SYSCALL_CALLBACK'],'')
                self.SQ.put((SysCall['UNREGISTER_SYSCALL_CALLBACK'],next(self.counter),m))

                #Stop the callback function cleanly
                q:queue.Queue = CALLBACK_QUEUE_LIST[syscall_name]['queue']     
                q.put("END") 


                #unregister the queue from the hashmap
                del CALLBACK_QUEUE_LIST[syscall_name]
            print(self.__user_Syscall)
        else:
            raise SysCallNotFoundError(f'Can not find syscall:{syscall_name}')
    
    def RegisterSyscallCallback(self,syscall_name,callback):

        q = queue.Queue(100)

        if syscall_name in CALLBACK_QUEUE_LIST:
            raise CallbackCollisionError("Can not register another event when already existing event registered.")
        
        print("[Debug] Register Callback for Syscall sent to bootstrap")
        msg = Message(SysCall['REGISTER_SYSCALL_CALLBACK'],{"callback_queue":q,'name':syscall_name})
        self.SQ.put((SysCall['REGISTER_SYSCALL_CALLBACK'],next(self.counter),msg))
        #th = threading.Thread(target=_callback_handler,args=(callback,q,self,))
        
        #store all the queue and threads in a list....
        CALLBACK_QUEUE_LIST[syscall_name] = {"queue":q,"uuid":msg.uuid}
        print("[Dubug] Callback Added to callback queue",CALLBACK_QUEUE_LIST)

        f = threading.Thread(target=_callback_handler,args=(callback,q,self,))
        f.daemon = True
        f.start()

        THREAD_CALLBACKS[syscall_name] = f

    def UnSyscallRegisterCallBack(self,syscall_name):
        if not syscall_name in self.__user_Syscall:
            raise SysCallNotFoundError(f'Given syscall {syscall_name} not found.')
        
        m = Message(SysCall['UNREGISTER_SYSCALL_CALLBACK'],{'name':syscall_name})
        self.SQ.put((SysCall['UNREGISTER_SYSCALL_CALLBACK'],next(self.counter),m))

        #Stop the callback function cleanly
        q:queue.Queue = CALLBACK_QUEUE_LIST[syscall_name]['queue']     
        q.put("END") 


        #unregister the queue from the hashmap
        del CALLBACK_QUEUE_LIST[syscall_name]
     
    def sendSyscall(self,syscall_name,msg):
    
        if not syscall_name in self.__user_Syscall:
            raise SysCallNotFoundError(f'Given syscall {syscall_name} not found.')
        
        m = Message(SysCall['SEND_SYSCALL'],{"msg":msg,'type':syscall_name})
        self.SQ.put((SysCall['SEND_SYSCALL'],next(self.counter),m))

    # Function for sending batch update....
    def sendBatch(self,batch:list[Message]):
        '''
        1. Send a list of Message class to the bootstrapper
        '''
        m = Message(SysCall['BATCH_UPDATE'],batch)
        self.SQ.put((SysCall['BATCH_UPDATE'],next(self.counter),m))
        

    #For handling Unmanaged Nodes
    def RegisterUnmanagedNode(self,id:str,tag:str):
        
        warnings.warn("UnManaged Nodes are not checked for existance. Developer must keep track of there existance."
        "   ->For detailed reference on how to manage custom dynamic nodes check PYUI documentation.")

        if id in self.id_map:
            raise IdCollisionError(f'Can not register unmanaged id:{id} as id of name:{id} already exists')
        
        node = PyUILayoutNode(tag)

        node.managed = False

        self.id_map[id] = node #add it to id map


    def UnRegisterUnmangedNode(self,id:str):
        if id not in self.id_map:
            raise IdNotFoundError(f'Given id:{id} does not exist,hence can not be unregistered')
        
        node:PyUILayoutNode = self.id_map[id]

        if node.managed == True:
            raise IllegalManagedNodeDeletionError(f'Managed node id:{id} is not allowed to be unregistered.' \
            'Warning:Forcefully using JS to delete managed nodes may cause unsync in certain areas in Python and JS runtimes')

        
    
        # Remove all callbacks 
        for idofcallback,typeofCallback in node.callbacks:
            self.UnRegisterCallBack(idofcallback,typeofCallback)

        
        #Delete reference from id map

        del self.id_map[id]

        #Issue warning for JS and python inconsistency
        warnings.warn("The given node with id:{id} has been unregistered from python dom tree.However developer must remove it from JS dom tree manually." \
        "   -> For reference check PYUI documentation.")
    #Functions for window control and propperty management inheritatated from pywebview and controlled allotment


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


class Pipeline:
    def __init__(self):
        self.steps = []

    def add(self, target):
        self.steps.append(
            target
        )

    def call(self,args:list[tuple]=[]):
        for target,arg in zip(self.steps,args):
                try:
                    res = target(*arg,ret=True)
                except Exception as ex:
                    print("Error in Hook update:",ex)
                    traceback.print_stack()
                    print("Exiting application.")
                    yield -1
                yield res
              



class Hook:
    '''
    PYUI Hooks
    '''
    def __init__(self,pipe:Pipeline,pyui:PYUI,fps:int=30):
        self.tp = 1/fps
        self.obj:PYUI = pyui
        self.pipe = pipe
        self.args = []
        self.q = queue.Queue()
        self.lock = threading.Lock()
        self.dirty = False

        pyui.thpool.submit(self.__hook_handler,self.q)
        th = threading.Thread(target=self.__hook_handler,args=(self.q))
        th.daemon = True

        th.start()

        msg = Message(SysCall['STOP_HOOKS'],self.q)
        self.obj.SQ.put((SysCall['STOP_HOOKS'],next(self.obj.counter),msg))

    
    def __hook_handler(self,msg_bus:queue.Queue):

        while True:
            try:
                msg = msg_bus.get_nowait()
                if msg == 'END':
                    break
            except:
                pass

            if self.dirty:
                with self.lock:
                    args = self.args
                self.flush(args)
                self.dirty = False

                time.sleep(self.tp)
            else:
                self.sleep()

            

    def flush(self,arg):
        msgs = []
        for j in self.pipe.call(arg):
            if j == -1:
                self.obj.End()
            msgs.append(j)
        

        self.obj.sendBatch(msgs)
    
    def sleep(self):
        time.sleep(self.tp)

    def update(self,args:list[tuple]=[]):
        with self.lock:
            self.args = args #update
            self.dirty = True
        
    def endHook(self):
        time.sleep(self.tp*2)
        self.q.put('STOP')