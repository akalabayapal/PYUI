

var SECRET_KEY = null;
var GLOBAL_CUSTOM_SYSCALL_MAP = {}; // Js object to store all the custom syscalls 

function getNestedValue(obj, path) {
    // If obj is invalid or path is not a string, return null
    if (!obj || typeof path !== 'string') return null;

    // Split the path by '.' and traverse the object
    const result = path.split('.').reduce((currentPath, key) => {
        // If at any point the path becomes undefined or null, return null
        if (currentPath === null || currentPath === undefined) {
            return null;
        }
        return currentPath[key];
    }, obj);

    // Ensure we return null if the final result is undefined
    return result !== undefined ? result : null;
}

function setNestedValue(obj, path, value) {
    // If obj is invalid or path is not a string, return false (operation failed)
    if (!obj || typeof path !== 'string') return false;

    const keys = path.split('.');
    let current = obj;

    for (let i = 0; i < keys.length; i++) {
        const key = keys[i];

        // If we are at the last key, set the value
        if (i === keys.length - 1) {
            current[key] = value;
            return true; // Success
        }

        // If the next nested level doesn't exist, or isn't an object, create it
        if (current[key] === undefined || current[key] === null || typeof current[key] !== 'object') {
            current[key] = {};
        }

        // Move deeper into the object tree
        current = current[key];
    }

    return false;
}

function register_sign(sign) {
    SECRET_KEY = sign;
}

async function standardSha256(message) {
    // 1. Encode text string into an array of bytes (UTF-8)
    const msgBuffer = new TextEncoder().encode(message);

    // 2. Compute the raw SHA-256 hash buffer natively
    const hashBuffer = await crypto.subtle.digest("SHA-256", msgBuffer);

    // 3. Convert the raw binary array buffer into a hex string
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");

    return hashHex;
}


async function computeHmac(message, secretKey) {
    const encoder = new TextEncoder();

    // 1. Convert text inputs into byte arrays
    const messageBytes = encoder.encode(message);
    const keyBytes = encoder.encode(secretKey);

    // 2. Import the raw secret key into the crypto engine
    const cryptoKey = await crypto.subtle.importKey(
        "raw",
        keyBytes,
        { name: "HMAC", hash: "SHA-256" },
        false,
        ["sign"]
    );

    // 3. Compute the raw binary signature
    const signatureBuffer = await crypto.subtle.sign("HMAC", cryptoKey, messageBytes);

    // 4. Convert the binary signature to a standard hexadecimal string
    const hashArray = Array.from(new Uint8Array(signatureBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
}


async function _HandleCallbackSend(uuid, socket, details) {

    //toSend = "{\"uuid\":\"" + uuid + "\",\"type\":\"CALLBACK\",\"data\":\"\"}";
    var toSend = { "uuid": uuid, "type": "CALLBACK", "data": details };

    send_str = JSON.stringify(toSend);

    //Get the sha-256 encoded string.
    var sha256_encoded_msg = await standardSha256(send_str);

    //make hmac 
    var hmac_code = await computeHmac(sha256_encoded_msg, SECRET_KEY);
    toSend['sign'] = hmac_code;
    GLOBAL_SOCKET.send(JSON.stringify(toSend)); //Send the msg back to python runtime


}
async function _HandleGrbContent(uuid, socket, value) {

    var toSend = { "uuid": uuid, "type": "GRAB_CONTENT", "data": value };

    var send_str = JSON.stringify(toSend);

    //Get the sha-256 encoded string.
    var sha256_encoded_msg = await standardSha256(send_str);

    //make hmac 
    hmac_code = await computeHmac(sha256_encoded_msg, SECRET_KEY);
    toSend['sign'] = hmac_code

    GLOBAL_SOCKET.send(JSON.stringify(toSend)); //Send the msg back to python runtime

}


function HandleStyleClass(args) {
    //args: id,action and class
    var id = args.id;
    var action = args.action;
    var cls = args.class;

    var ele = document.getElementById(id);

    if (ele) {
        if (action == 'ADD') {
            ele.classList.add(cls);
        }
        else if (action == 'REMOVE') {
            ele.classList.remove(cls);
        }
        else if (action == 'TOGGLE') {
            ele.classList.toggle(action);
        }
    }


}


async function verifyIncomingMessage(incomingMsg) {
    // 1. Extract the signature and remove it from the object we want to hash
    const incomingSig = incomingMsg.sign;
    delete incomingMsg.sign;

    // 3. Sort keys and flatten (uuid is naturally included now!)
    const sortedKeys = Object.keys(incomingMsg).sort();
    let flatString = JSON.stringify(incomingMsg);

    // 4. Hash, compare, and burn
    const dataHash = await standardSha256(flatString);
    const expectedSig = await computeHmac(dataHash, SECRET_KEY);

    //console.log(flatString,dataHash);


    if (incomingSig !== expectedSig) {
        return false;
    }

    return true;
}


//Function for binding JS functions with Python syscall
async function bind(syscall, callback) {

    //Assign the syscall to GLOBAL CUSTOM SYSCALL MAP
    GLOBAL_CUSTOM_SYSCALL_MAP[syscall] = callback;

}

function generateUUID() {
    return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

async function sendSyscall(syscall, msg) {
    if (!syscall) {
        return;
    }
    var call = GLOBAL_CUSTOM_SYSCALL_MAP[syscall];
    if (call) {
        var toSend = { "data": msg, "type": syscall, "uuid": generateUUID() };

        send_str = JSON.stringify(toSend);

        //Get the sha-256 encoded string.
        sha256_encoded_msg = await standardSha256(send_str);

        //make hmac 
        hmac_code = await computeHmac(sha256_encoded_msg, SECRET_KEY);
        toSend['sign'] = hmac_code


        GLOBAL_SOCKET.send(JSON.stringify(toSend));
    }
    else {
        console.log("Error:The callback " + syscall + " is not registered.");
    }
}




class Msghandler {
    constructor(socket) {

        this.socket = socket;
        this.callBackWrappers = new Object({});
        this.processed_map = new Object({});

    }


    async evaluateMsg(jsonMessage) {

        var type = jsonMessage.type;
        var uuid = jsonMessage.uuid;



        if (!(uuid in this.processed_map) && await verifyIncomingMessage(jsonMessage)) {
            if (type == "EXECUTE_ONLY") {

                //add it to processed list to maintain at most one call
                this.processed_map[uuid] = true;

                var content = jsonMessage.data;
                this.handleExecuteJs(content);

            }

            else if (type == "REGISTER_CALLBACK") {
                var id = jsonMessage.id;
                var typeCallback = jsonMessage.callback_type;
                var wrapper = this.registerCallback(id, typeCallback, uuid);

                var container = { wrap: wrapper, type: typeCallback, Eleid: id };
                this.callBackWrappers[uuid] = container;
                //console.log("Callback wrappers:",JSON.stringify(this.callBackWrappers));
            }
            else if (type == "UNREGISTER_CALLBACK") {

                //console.log("Callback wrappers:",JSON.stringify(this.callBackWrappers));

                try {

                    var uuid_callback = jsonMessage.id;
                    const cont = this.callBackWrappers[uuid_callback];
                    const id = cont.Eleid;
                    const type = cont.type;
                    const wrap = cont.wrap;
                    document.getElementById(id).removeEventListener(type, wrap);

                    delete this.callBackWrappers[uuid_callback];
                }
                catch (ex) {
                    console.log("[Error] Can not remove callback", ex);

                }
            }
            else if (type == "GRAB_CONTENT") {
                var id = jsonMessage.id;
                var attrib = jsonMessage.attrib;

                var element = document.getElementById(id);

                const val = getNestedValue(element,attrib);

                if (attrib == 'text') {
                    var value = element.textContent;
                }
                else if (val != null) {

                    if (
                        typeof val === "string" ||
                        typeof val === "number" ||
                        typeof val === "boolean"
                    ) {
                        var value = val;
                    }
                    else {
                        var value = element.getAttribute(attrib);

                    }
                }
                else {
                    var value = element.getAttribute(attrib);

                }
                
                if(!value){
                    console.log(`Error:No attribute ${attrib} found for id:${id}`);
                }

                _HandleGrbContent(uuid, this.socket, value);
            }


            else if (type == "BATCH_UPDATE") {

                //To update multiple things at once...

                for (let index = 0; index < jsonMessage.batch.length; index++) {
                    this.evaluateMsg(jsonMessage.batch[index]);

                }
            }


            else {

                //Check if some custom syscall is present if present call it

                var callback = GLOBAL_CUSTOM_SYSCALL_MAP[type];
                if (callback) {
                    callback(jsonMessage);
                }
                else {
                    console.log("[Error] No associated callback for custom syscall:" + type);
                }
            }

        }
        else {
            
            console.log("Wrong uuid or signature did not match.Hence dropping the packet.");
        }
    }

    async handleExecuteJs(js_content) {

        var execution_type = js_content.js_type;
        var args = js_content.args;

        if (execution_type == 'updateText') {

            //We need text:value and id:id
            var text = args.text;
            var id = args.id;

            //Update the text
            var ele = document.getElementById(id);

            if (ele) {
                ele.textContent = text;
            }
        }
        else if (execution_type == 'update') {

            //We need value:value, id:id and att:attribute
            var id = args.id;
            var value = args.value;
            var att = args.att;
            var ele = document.getElementById(id);


            // try to set it 

            const set = setNestedValue(ele, att, value);

            if (!set) {
                if (ele) {
                    ele.setAttribute(att, value);
                }
                else{
                    console.log(`Error:No attribute/property:${att} found for id:${id}`);
                }
            }

        }
        else if (execution_type == 'updateStyle') {

            //We need id:id , att:attribute and value:value
            var id = args.id;
            var value = args.value;
            var att = args.att;

            var ele = document.getElementById(id);

            if (att in ele.style) {

                ele.style[att] = value;
            }
            else {
                console.log(`Error: No style attribute named:${att} found for id:${id}.`)
            }

        }
        else if (execution_type == 'addstyleclass') {
            HandleStyleClass(args);
        }
        else if (execution_type == 'remove') {

            var id = args.id;
            var att = args.att;
            var ele = document.getElementById(id);
            ele.removeAttribute(att);

        }
    }

    async registerCallback(id, eventType, uuid) {

        //To handle the REGISTER_CALLBACK syscalls...
        var element = document.getElementById(id);
        var wrapper = (event) => {


            if (event.detail) {
                _HandleCallbackSend(uuid, this.socket, event.detail);

            }
            else {
                _HandleCallbackSend(uuid, this.socket, "");

            }
        };

        if (element) {
            element.addEventListener(eventType, wrapper);
        }

        return wrapper;


    }

}

// Handler for adding a node

/**
 * TO add a custom node 
 * @param {string} parent_id - the id of the parent
 * @param {string} html_to_add - the html node
 * @param {string} mode - mode of addition append | top } after
 */
function addNode(parent_id, html_to_add, mode) {


    // 1. Select the parent node
    const parentElement = document.getElementById(parent_id);

    // 2. Define your raw HTML string
    const rawHTML = html_to_add;

    // 3. Append the raw HTML directly
    if (mode === 'append') {
        parentElement.insertAdjacentHTML('beforeend', rawHTML);
    }
    else if (mode === 'top') {
        parentElement.insertAdjacentHTML('afterbegin', rawHTML);

    }
    else if (mode == 'after') {
        parentElement.insertAdjacentHTML('afterend', rawHTML);
    }

}

function remNode(node_id) {

    const element = document.getElementById(node_id);
    element.remove();
}

/**
 * 
 * @param {string} msg - the json message from the python runtime format:{'parent_id','html_to_add'}
 */
function addNodeHandler(msg) {


    const message = JSON.parse(msg.msg);

    const parent_id = message.parent_id;
    const html_to_add = message.html_to_add;
    const mode = message.mode;




    addNode(
        parent_id,
        html_to_add,
        mode
    );
}

/**
 * 
 * @param {string} msg - The message string json
 */
function remNodeHandler(msg) {

    const message = JSON.parse(msg.msg);

    remNode(message.id);

}

bind('ADD_NODE_END', addNodeHandler);
bind('REM_NODE', remNodeHandler);