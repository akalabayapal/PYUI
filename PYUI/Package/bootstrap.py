'''
This is the initial runtime script
'''

import pickle
from PYUI.pyuinode import PyUILayoutNode
import webview
import asyncio
import threading
import inspect
import time
import websockets
import queue
import uuid
import json
import multiprocessing
import itertools 
import importlib
import os
import sys
import hmac
import hashlib
import secrets
from PYUI.Package.PYUI import PYUI

class UnkownSyscallUpdate(Exception):
    pass


# =====================================================================
# CONFIGURATION AND SANITIZATION LAYER
# =====================================================================
DEFAULT_WINDOW_CONFIG = {
    "title": "PyUI Application",
    "url": None,
    "html": None,
    "width": 800,
    "height": 600,
    "x": None,
    "y": None,
    "screen": None,
    "resizable": True,
    "fullscreen": False,
    "min_size": (200, 100),
    "hidden": False,
    "frameless": False,
    "easy_drag": True,
    "shadow": False,
    "focus": True,
    "minimized": False,
    "maximized": False,
    "menu": [],
    "on_top": False,
    "confirm_close": False,
    "background_color": "#FFFFFF",
    "transparent": False,
    "text_select": False,
    "zoomable": False,
    "draggable": False,
    "vibrancy": False,
    "server_args": {},
    "localization": None,
}

#=====================================================================
# GLOBALS
#=====================================================================
# Keep track of active UI connections globally for the prototype

ACTIVE_CONNECTIONS = set()

SEND_QUEUE = queue.PriorityQueue(100) #Main static queue for handling the sockets

MAIN_THREAD_QUEUE = queue.Queue(100) #for the new form notice

CALLBACK_HASHMAP = {}

GRB_HASHMAP = {}

global_counter = itertools.count()


# Create a proper thread-safe signaling flag near your other globals
KERNEL_READY = threading.Event()

# Global reference to the engine's main asynchronous network event loop
ASYNC_LOOP = None

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

SYSCALL_CALLBACK = {

}

UUID_PROCESSED = {}

HOOK_QUEUE = []

is_first = True

ASSIGNED_PORT = queue.Queue(1)

class ConsoleRouter:
    def log(self, message):
        # This catches anything sent from JS and prints it in your Python terminal
        print(f"[JS Console] {message}")

# Generate a secure 32-byte (256-bit) secret key
# This utilizes your OS's highest-quality randomness source (like /dev/urandom)
secret_bytes = secrets.token_bytes(32)

# If you need to inject it into JS as a plain text string, 
# convert it to a hex string (which results in a 64-character string)
secret_hex_string = secret_bytes.hex()



def flatten_and_hash(payload: dict) -> str:
    
    # Sort keys alphabetically to guarantee structural determinism
    flat_string = json.dumps(payload, separators=(',', ':'))
    return hashlib.sha256(flat_string.encode('utf-8')).hexdigest()


def generate_message_signature(payload: dict,uuid, secret_key: str) -> str:
    # Calculate the stable data hash
    data_hash = flatten_and_hash(payload)
    # HMAC the hash with the secret key
    signature = hmac.new(secret_key.encode(), data_hash.encode(), hashlib.sha256).hexdigest()

    return signature




def resource_path(*parts):
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base, *parts)

def inject(port:int):
    WEBSOCKET_INJECTION = """
            connectSocket("""+str(port)+""");
            register_sign('"""+secret_hex_string+"""');
    """

    return WEBSOCKET_INJECTION
#=====================================================================

class Message:
    def __init__(self, syscall, msg: str = ""):
        self.syscall = syscall
        self.msg = msg
        self.uuid = str(uuid.uuid4()).replace("'", "")

#=====================================================================
# SANITIZE THE CONFIG 
#=====================================================================
def sanitize_window_config(config: dict) -> dict:
    boolean_keys = {
        "resizable", "fullscreen", "hidden", "frameless", "easy_drag", 
        "shadow", "focus", "minimized", "maximized", "on_top", 
        "confirm_close", "transparent", "text_select", "zoomable", 
        "draggable", "vibrancy"
    }
    int_keys = {"width", "height", "x", "y"}
    injected = {"url", "js_api"}
    
    sanitized = config.copy()
    
    for key, value in sanitized.items():
        if value is None:
            continue
            
        if key in injected:
            continue

        if key in boolean_keys:
            if isinstance(value, str):
                sanitized[key] = value.strip().lower() in ("true", "1", "yes")
            else:
                sanitized[key] = bool(value)
                
        elif key in int_keys:
            try:
                sanitized[key] = int(value)
            except (ValueError, TypeError):
                pass
                
        elif key == "min_size":
            if isinstance(value, str):
                try:
                    parts = value.split(",")
                    sanitized[key] = (int(parts[0]), int(parts[1]))
                except (IndexError, ValueError):
                    sanitized[key] = (200, 100)
            elif isinstance(value, (list, tuple)):
                sanitized[key] = (int(value[0]), int(value[1]))

    return sanitized


class KernelProxy:
    """
    Wraps an internal class containing async functions, 
    making all its methods look completely synchronous to the developer.
    """
    def __init__(self, target_instance):
        self._target = target_instance

    def __getattr__(self, name):
        # 1. Grab the actual async function from our hidden target instance
        attr = getattr(self._target, name)
        
        # 2. If it's an async function, intercept it and route it through the loop
        if inspect.iscoroutinefunction(attr):
            def synchronous_wrapper(*args, **kwargs):
                coro = attr(*args, **kwargs)
                future = asyncio.run_coroutine_threadsafe(coro, ASYNC_LOOP)
                return future.result()
            return synchronous_wrapper
            
        return attr

# =====================================================================
# WEBSOCKET CORE ENGINE
# =====================================================================

class MsgHandler:

    @staticmethod
    async def EXECUTE_JS(msg,isbatch=False):
        if isbatch:
            toSend = {"uuid": msg.uuid, "type": "EXECUTE_ONLY", "data": msg.msg}
        else:
            toSend = {"uuid": msg.uuid, "type": "EXECUTE_ONLY", "data": msg.msg,"count":next(global_counter)}

        sign = generate_message_signature(toSend,msg.uuid,secret_hex_string)
        toSend['sign'] = sign
        return toSend
    
    @staticmethod
    async def REGISTER_CALLBACK(msg,isbatch=False):
    
        idEle = msg.msg['id'] #get id of the callback

        typeOfCallback = msg.msg['callback_type'] #get the event listener type
        q = msg.msg['callback_queue'] #get the queue
        CALLBACK_HASHMAP[msg.uuid] = q #register the callback to a hashmap

        if isbatch:
            toSend = {"uuid": msg.uuid, "type": "REGISTER_CALLBACK", "id": idEle,"callback_type":typeOfCallback}
        else:
            toSend = {"uuid": msg.uuid, "type": "REGISTER_CALLBACK", "id": idEle,"callback_type":typeOfCallback,"count":next(global_counter)}

        sign = generate_message_signature(toSend,msg.uuid,secret_hex_string)
        toSend['sign'] = sign

        return toSend
    
    @staticmethod
    async def UNREGISTER_CALLBACK(msg,isbatch=False):
        uid = msg.msg #get id of the callback
        if isbatch:
            toSend = {"uuid": msg.uuid, "id": uid,"type":'UNREGISTER_CALLBACK'}
        else:
            toSend = {"uuid": msg.uuid, "id": uid,"type":'UNREGISTER_CALLBACK',"count":next(global_counter)}
        
        del CALLBACK_HASHMAP[uid]

        sign = generate_message_signature(toSend,msg.uuid,secret_hex_string)
        toSend['sign'] = sign

        return toSend
    
    @staticmethod
    async def CONTENT_GRAB(msg,isbatch=False):
        uid = msg.msg['id']
        attrib = msg.msg['attrib']
  

        GRB_HASHMAP[msg.uuid] = msg.msg['queue']

        if isbatch:
            toSend = {"uuid": msg.uuid, "id": uid,"attrib":attrib,"type":'GRAB_CONTENT'}
        else:
            toSend = {"uuid": msg.uuid, "id": uid,"attrib":attrib,"type":'GRAB_CONTENT',"count":next(global_counter)}


        sign = generate_message_signature(toSend,msg.uuid,secret_hex_string)
        toSend['sign'] = sign

        return toSend
    
    @staticmethod
    async def SYSCALL(msg,isbatch=False):
        type_syscall = msg.msg['type']
        msg_call = msg.msg['msg']
        if isbatch:
            toSend = {"uuid": msg.uuid,"type":type_syscall,'msg':msg_call}
        else:
            toSend = {"uuid": msg.uuid,"type":type_syscall,'msg':msg_call,"count":next(global_counter)}


        sign = generate_message_signature(toSend,msg.uuid,secret_hex_string)
        toSend['sign'] = sign

        return toSend
    


    

    


async def Handle_Send(websocket):
    is_started = False
    print(f"[WebSocket Core] Polling Loop Active. Queue Memory Address: {id(SEND_QUEUE)}")
    while True:
        try:
            # 1. Attempt to grab an item instantly without checking .empty()
            priority,time,msg = SEND_QUEUE.get_nowait()
        except queue.Empty:
            # 2. If the queue is truly empty, yield control to the loop immediately
            await asyncio.sleep(0.016)  # ~60fps poll interval
            continue

        if msg.syscall == SysCall['START'] and not  is_started:
            print("START command received...")
            is_started = True
            SEND_QUEUE.task_done()
            continue
        
        if msg.syscall == SysCall['START'] and is_started:
            print("DEBUG: Cannot start already started procedure...")
            SEND_QUEUE.task_done()
            continue

        if not is_started:
            print("Can not process event until Queue Started")
            SEND_QUEUE.task_done()
            continue

        if msg.syscall == SysCall['EXECUTE_JS']:
           
            toSend = await MsgHandler.EXECUTE_JS(msg)

            try:
                await websocket.send(json.dumps(toSend))
                #print("[Network Thread] Core socket flush successful! Data left the Python runtime layer.")
            except Exception as net_err:
                print(f"[Network Thread] CRITICAL CRASH DURING SEND: {net_err}")
                break

        elif msg.syscall == SysCall['REGISTER_CALLBACK']:
            
            toSend = await MsgHandler.REGISTER_CALLBACK(msg)

            try:
                await websocket.send(json.dumps(toSend))
                #print("[Network Thread] Core socket flush successful! Data left the Python runtime layer.")
            except Exception as net_err:
                print(f"[Network Thread] CRITICAL CRASH DURING SEND: {net_err}")
                break

        elif msg.syscall == SysCall['UNREGISTER_CALLBACK']:


            toSend = await MsgHandler.UNREGISTER_CALLBACK(msg)

            try:
                await websocket.send(json.dumps(toSend))
                #print("[Network Thread] Core socket flush successful! Data left the Python runtime layer.")
            except Exception as net_err:
                print(f"[Network Thread] CRITICAL CRASH DURING SEND: {net_err}")
                break

        elif msg.syscall == SysCall['CONTENT_GRAB']:

            toSend = await MsgHandler.CONTENT_GRAB(msg)

            try:
                await websocket.send(json.dumps(toSend))
                #print("[Network Thread] Core socket flush successful! Data left the Python runtime layer.")
            except Exception as net_err:
                print(f"[Network Thread] CRITICAL CRASH DURING SEND: {net_err}")
                break


        elif msg.syscall == SysCall['REGISTER_SYSCALL_CALLBACK']:

            queue_callback = msg.msg['callback_queue']
            name = msg.msg['name']
            SYSCALL_CALLBACK[name] = queue_callback
            #print("[BOOTS] Callback registered:",SYSCALL_CALLBACK)

        elif msg.syscall == SysCall['UNREGISTER_SYSCALL_CALLBACK']:

            name = msg.msg['name']
            del SYSCALL_CALLBACK[name]

        elif msg.syscall == SysCall['SEND_SYSCALL']:

            toSend = await MsgHandler.SYSCALL(msg)

            try:
                await websocket.send(json.dumps(toSend))
                #print("[Network Thread] Core socket flush successful! Data left the Python runtime layer.")
            except Exception as net_err:
                print(f"[Network Thread] CRITICAL CRASH DURING SEND: {net_err}")
                break

        elif msg.syscall == SysCall['STOP_HOOKS']:
            HOOK_QUEUE.append(msg.msg)

        elif msg.syscall == SysCall['BATCH_UPDATE']:
            '''
            Take each of the msg and put it to the queue.
            '''
            funcmap = {SysCall['EXECUTE_JS']:MsgHandler.EXECUTE_JS,
                       SysCall['REGISTER_CALLBACK']:MsgHandler.REGISTER_CALLBACK,
                       SysCall['UNREGISTER_CALLBACK']:MsgHandler.UNREGISTER_CALLBACK,
                       SysCall['CONTENT_GRAB']:MsgHandler.CONTENT_GRAB,
                       SysCall['SEND_SYSCALL']:MsgHandler.SYSCALL
                       }
            toSendDict = []
            for message in msg.msg:
                toSendDict.append(await funcmap[message.syscall](message,True))
            
            
            toSend = {'type':'BATCH_UPDATE','batch':toSendDict,"count":-1}
            toSend['sign'] = generate_message_signature(toSend,msg.uuid,secret_hex_string)
        
            try:
                await websocket.send(json.dumps(toSend))
                #print("[Network Thread] Core socket flush successful! Data left the Python runtime layer.")
            except Exception as net_err:
                print(f"[Network Thread] CRITICAL CRASH DURING SEND: {net_err}")
                break
            


        elif msg.syscall == SysCall['END']:
            print("Ending websockets....")
            MAIN_THREAD_QUEUE.put(Message(SysCall['END']))
            SEND_QUEUE.task_done()
            break

        SEND_QUEUE.task_done()
    
async def listen_for_messages(websocket):
    try:
        async for message in websocket:

            val:dict = json.loads(message)
       
            if not val.get('uuid') or (val.get('uuid') in UUID_PROCESSED and val.get('type') in SYSCALL_CALLBACK):
                #drop the packet
                print("[Packet Dropped] Packet did not have uuid or blocked due to atmost one policy.")
            
 
            elif val['type'] == 'CALLBACK':
                signCame = val.get('sign')
                if signCame:
                    del val['sign']
                
                    signExpected = generate_message_signature(val,'',secret_hex_string)
                
                    q:queue.Queue = CALLBACK_HASHMAP.get(val['uuid'])
                
                    if q and (signExpected == signCame):
                        q.put(Message(SysCall['POLL']))
                    else:
                        print("[Packet Dropped] Packed did not have valid registered callback registered or signature of data is not matched.")
                else:

                    print("[Packet Dropped] The packet did not have valid signature.")

                UUID_PROCESSED[val.get('uuid')] = True

                

            elif val['type'] == 'GRAB_CONTENT':

                signCame = val.get('sign')
                if signCame:
                    del val['sign']

                    q:queue.Queue = GRB_HASHMAP.get(val['uuid'])
                    signExpected = generate_message_signature(val,'',secret_hex_string)

                    if q and  (signCame == signExpected):
                        q.put(val.get('data'))
                    else:
                        print("[Packet Dropped] The packet signature did not match the content streamed.")

                else:
                    print("[Packet Dropped] The packet did not have valid signature.")
                
                UUID_PROCESSED[val.get('uuid')] = True
                
            elif val.get('type') in SYSCALL_CALLBACK:
                
                signCame = val.get('sign')
                if signCame:
                    del val['sign']
                    signExpected = generate_message_signature(val,'',secret_hex_string)
                    data_sent = val.get("data")
                    q = SYSCALL_CALLBACK[val.get('type')]
                    q.put(data_sent)
                else:
                    print("[Packet Dropped] The packet did not have valid signature.")
          
            else:
                MAIN_THREAD_QUEUE.put(Message(SysCall['END']))
                raise UnkownSyscallUpdate(f'Error:Unregistered syscall:{val['type']} arrived from JS interface.')
            
            UUID_PROCESSED[val.get('uuid')] = True

           # print("[WebSocket Server] Received from UI:",json.loads(message))
    except websockets.exceptions.ConnectionClosed:
        pass

async def handle_client(websocket: websockets):
    print(f"[WebSocket Server] UI Client connected: {websocket.remote_address}")

    # Directly send a START command after cleaning queue
    msg = Message(SysCall['START'],'')
    SEND_QUEUE.put((SysCall['START'],time.time(),msg))

    ACTIVE_CONNECTIONS.add(websocket)

    # 1. Create individual tasks for the bidirectional pipelines
    listener_task = asyncio.create_task(listen_for_messages(websocket))
    sender_task = asyncio.create_task(Handle_Send(websocket))

    # 2. Monitor both tasks. If either fails (e.g., connection drops), drop the whole group
    done, pending = await asyncio.wait(
        [listener_task, sender_task],
        return_when=asyncio.FIRST_COMPLETED
    )

    # 3. Cleanly cancel the lingering task so it doesn't leave zombie loops
    for task in pending:
        task.cancel()

    print("[WebSocket Server] Client connection terminated cleanly. Awaiting reconnection...")
    ACTIVE_CONNECTIONS.discard(websocket)

        





#=====================================================================
# MAIN function last stage of bootloader the control is handed over to the enrty point from here
#=====================================================================
def MAIN(PYUIObj:PYUI,window:webview.Window,entrymodule):

    global WINDOW
    
    # Suspends the thread cleanly until the WebSocket loop is allocated
    KERNEL_READY.wait()

    while ASSIGNED_PORT.empty():
        time.sleep(0.1)
        continue

    port = ASSIGNED_PORT.get()
    window.evaluate_js(inject(port))

    WINDOW = window
        

    print("Starting communication....")
    PYUIObj._startCommunication()

    print("Handing the control to entry point...")
 
    # Your dynamic string variable
    print("Module loaded:"+entrymodule)
    # Combine into a full absolute path: "code.login_form"
    module_path = f"code.{entrymodule}"
    form_module = importlib.import_module(module_path)
    form_module.entry(PYUIObj)
       
    # except Exception as ex:
    #     print("[BOOTSTRAP_SRIPT]Error in procedure:",ex)
    #     PYUIObj.End()

    



def start_websocket_server():
    global ASYNC_LOOP
    
    # Create the loop manually for this independent thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ASYNC_LOOP = loop  # Capture reference for the PyUI API layer

    
    async def main():
        async with websockets.serve(handle_client, "127.0.0.1", 0) as server :

            port = server.sockets[0].getsockname()[1]
            ASSIGNED_PORT.put(port)
            
            print(f"[WebSocket Server] Initialized on ws://127.0.0.1:{port} ...")

            KERNEL_READY.set() #Release the MAIN block 

            print("[WebSocket Server] The MAIN() execution resumed")

            await asyncio.Future()  # Infinite runtime block

    try:
        
        loop.run_until_complete(main())
    except Exception as e:
        
        print(f"[WebSocket Server] Core Loop Crash: {e}")
    finally:
        MAIN_THREAD_QUEUE.put(Message(SysCall['END'],""))
        loop.close()

# ... [Keep your sanitize_window_config and DEFAULT_WINDOW_CONFIG as is] ...

# =====================================================================
# THE SINGLE TRUE EXECUTION ENTRYPOINT
# =====================================================================


def MainQueueReader(window):
    while True:
        item:Message = MAIN_THREAD_QUEUE.get()
        if item.syscall == SysCall['END']:
            try:
                window.destroy()
            except:
                pass
            for q in CALLBACK_HASHMAP:
                qu = CALLBACK_HASHMAP[q]
                qu.put("END")
            for q in SYSCALL_CALLBACK:
                qu = SYSCALL_CALLBACK[q]
                qu.put("END")
            for q in HOOK_QUEUE:
                q.put("END")
            break
        if item.syscall == SysCall['NEW_FORM_LAUNCH']:
            ctx = multiprocessing.get_context('spawn')
            p = ctx.Process(target=BootStrapper,args=(item.msg,))
            p.start()
            



def BootStrapper(entryfile):
    print("[Main Thread] Parsing binary environment layout...")
    
    try:
        load = pickle.load(open(resource_path('compiled_layouts/'+entryfile+'.bin'), 'rb'))

        settings_map = load['form_settings']
        for key in settings_map:
            DEFAULT_WINDOW_CONFIG[key] = str(settings_map[key])
    except Exception as e:
        print(f"[Warning] Failed to load index.bin.Error: {e}")
        exit(1)

    sanitized_settings = sanitize_window_config(DEFAULT_WINDOW_CONFIG)
    sanitized_settings['url'] = 'layouts/'+entryfile+'.html'


    router = ConsoleRouter()
    window = webview.create_window(**sanitized_settings,js_api=router)
    

    PYUIObj = KernelProxy(PYUI(SQ=SEND_QUEUE,MQ=MAIN_THREAD_QUEUE,window=window,infoDict=load,syscall=SysCall))

    # 1. Spin up the background MAIN thread (Back to a standard thread wrapper!)
    print("[Main Thread] Launching MAIN program thread...")
    program_thread = threading.Thread(target=MAIN, args=(PYUIObj,window,entryfile,), daemon=True)
    program_thread.start()

    # 2. Spin up the background WebSocket thread
    print("[Main Thread] Launching asynchronous network worker thread...")
    ws_thread = threading.Thread(target=start_websocket_server, daemon=True)
    ws_thread.start()
    
    time.sleep(0.2)

    print("[Main Thread] Transferring thread focus to native GUI frame.")
    webview.start(MainQueueReader,args=window)
    MAIN_THREAD_QUEUE.put(Message(SysCall["END"]))

    print("[Main Thread] Window closed cleanly. Application terminating.")
   
if __name__ == "__main__":
    multiprocessing.freeze_support()
    BootStrapper('index')
  



