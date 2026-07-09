var SECRET_KEY = null;
var GLOBAL_CUSTOM_SYSCALL_MAP = {}; // Js object to store all the custom syscalls 

function getNestedValue(obj, path) {
    if (!obj || typeof path !== 'string') return null;

    const result = path.split('.').reduce((currentPath, key) => {
        if (currentPath === null || currentPath === undefined) {
            return null;
        }
        return currentPath[key];
    }, obj);

    return result !== undefined ? result : null;
}

function deleteNestedValue(obj, path) {
    if (!obj || typeof path !== 'string') return false;

    const keys = path.split('.');
    let current = obj;

    for (let i = 0; i < keys.length; i++) {
        const key = keys[i];

        if (current === null || current === undefined || !(key in current)) {
            return false;
        }

        if (i === keys.length - 1) {
            delete current[key];
            return true;
        }

        current = current[key];
    }

    return false;
}

function setNestedValue(obj, path, value) {
    if (!obj || typeof path !== 'string') return false;

    const keys = path.split('.');
    let current = obj;

    for (let i = 0; i < keys.length; i++) {
        const key = keys[i];

        if (i === keys.length - 1) {
            current[key] = value;
            return true;
        }

        if (current[key] === undefined || current[key] === null || typeof current[key] !== 'object') {
            current[key] = {};
        }

        current = current[key];
    }

    return false;
}

function register_sign(sign) {
    SECRET_KEY = sign;
}

async function standardSha256(message) {
    const msgBuffer = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest("SHA-256", msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
}

async function computeHmac(message, secretKey) {
    const encoder = new TextEncoder();
    const messageBytes = encoder.encode(message);
    const keyBytes = encoder.encode(secretKey);

    const cryptoKey = await crypto.subtle.importKey(
        "raw",
        keyBytes,
        { name: "HMAC", hash: "SHA-256" },
        false,
        ["sign"]
    );

    const signatureBuffer = await crypto.subtle.sign("HMAC", cryptoKey, messageBytes);
    const hashArray = Array.from(new Uint8Array(signatureBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
}

async function _HandleCallbackSend(uuid, socket, details) {
    var toSend = { "uuid": uuid, "type": "CALLBACK", "data": details };
    var send_str = JSON.stringify(toSend);
    var sha256_encoded_msg = await standardSha256(send_str);
    var hmac_code = await computeHmac(sha256_encoded_msg, SECRET_KEY);
    toSend['sign'] = hmac_code;
    GLOBAL_SOCKET.send(JSON.stringify(toSend));
}

async function _HandleGrbContent(uuid, socket, value) {
    var toSend = { "uuid": uuid, "type": "GRAB_CONTENT", "data": value };
    var send_str = JSON.stringify(toSend);
    var sha256_encoded_msg = await standardSha256(send_str);
    var hmac_code = await computeHmac(sha256_encoded_msg, SECRET_KEY);
    toSend['sign'] = hmac_code;
    GLOBAL_SOCKET.send(JSON.stringify(toSend));
}

function HandleStyleClass(args) {
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
            ele.classList.toggle(cls); // ✅ FIXED: Changed 'action' to 'cls'
        }
    }
}

async function verifyIncomingMessage(incomingMsg) {
    const incomingSig = incomingMsg.sign;
    delete incomingMsg.sign;

    const sortedKeys = Object.keys(incomingMsg).sort();
    let flatString = JSON.stringify(incomingMsg);

    const dataHash = await standardSha256(flatString);
    const expectedSig = await computeHmac(dataHash, SECRET_KEY);

    if (incomingSig !== expectedSig) {
        return false;
    }
    return true;
}

async function bind(syscall, callback) {
    GLOBAL_CUSTOM_SYSCALL_MAP[syscall] = callback;
}

function generateUUID() {
    return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

async function sendSyscall(syscall, msg) {
    if (!syscall) return;
    var call = GLOBAL_CUSTOM_SYSCALL_MAP[syscall];
    if (call) {
        var toSend = { "data": msg, "type": syscall, "uuid": generateUUID() };
        var send_str = JSON.stringify(toSend);
        var sha256_encoded_msg = await standardSha256(send_str);
        var hmac_code = await computeHmac(sha256_encoded_msg, SECRET_KEY);
        toSend['sign'] = hmac_code;
        GLOBAL_SOCKET.send(JSON.stringify(toSend));
    }
    else {
        console.error("The callback " + syscall + " is not registered.");
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
                this.processed_map[uuid] = true;
                var content = jsonMessage.data;
                this.handleExecuteJs(content);
            }
            else if (type == "REGISTER_CALLBACK") {
                var id = jsonMessage.id;
                var typeCallback = jsonMessage.callback_type;
                var signal = await this.registerCallback(id, typeCallback, uuid);
                var container = { signal: signal, type: typeCallback, Eleid: id };
                this.callBackWrappers[uuid] = container;
            }
            else if (type == "UNREGISTER_CALLBACK") {
                try {
                    var uuid_callback = jsonMessage.id;
                    const cont = this.callBackWrappers[uuid_callback];
                    const id = cont.Eleid;
                    const type = cont.type;
                    const signal = cont.signal;
                    
                    signal.abort();
                    delete this.callBackWrappers[uuid_callback];
                }
                catch (ex) {
                    console.warn("[Error] Can not remove callback", ex);
                }
            }
            else if (type == "GRAB_CONTENT") {
                var id = jsonMessage.id;
                var attrib = jsonMessage.attrib;
                var element = document.getElementById(id);
                const val = getNestedValue(element, attrib);
                var value = null;

                if (attrib.includes(":")) {
                    const style = attrib.split(":")[1];
                    const computed_style = window.getComputedStyle(element);
                    
                    if (style === 'all') {
                        value = computed_style;
                    }
                    else if (style in computed_style) {
                        value = computed_style[style];
                    }
                    else {
                        console.error(`No style attribute ${style} found for id:${id}`);
                        return;
                    }
                }
                else if (attrib == 'text') {
                    value = element.textContent;
                }
                else if (val !== null && val !== undefined) { // ✅ FIXED: Explicit nullish check
                    if (
                        typeof val === "string" ||
                        typeof val === "number" ||
                        typeof val === "boolean"
                    ) {
                        value = val;
                    }
                    else {
                        value = element.getAttribute(attrib);
                    }
                }
                else {
                    value = element.getAttribute(attrib);
                }
                
                // ✅ FIXED: Only throw error if the value is truly missing (null/undefined)
                if (value === null || value === undefined) {
                    console.error(`No attribute ${attrib} found for id:${id}`);
                }

                _HandleGrbContent(uuid, this.socket, value);
            }
            else if (type == "BATCH_UPDATE") {
                for (let index = 0; index < jsonMessage.batch.length; index++) {
                    this.evaluateMsg(jsonMessage.batch[index]);
                }
            }
            else {
                var callback = GLOBAL_CUSTOM_SYSCALL_MAP[type];
                if (callback) {
                    callback(jsonMessage);
                }
                else {
                    console.error("[Error] No associated callback for custom syscall:" + type);
                }
            }
        }
        else {
            console.warn("Wrong uuid or signature did not match. Hence dropping the packet.");
        }
    }

    async handleExecuteJs(js_content) {
        var execution_type = js_content.js_type;
        var args = js_content.args;

        if (execution_type == 'updateText') {
            var text = args.text;
            var id = args.id;
            var ele = document.getElementById(id);
            if (ele) {
                ele.textContent = text;
            }
        }
        else if (execution_type == 'update') {
            var id = args.id;
            var value = args.value;
            var att = args.att;
            var ele = document.getElementById(id);

            const set = setNestedValue(ele, att, value);
            if (!set) {
                if (ele) {
                    ele.setAttribute(att, value);
                }
                else {
                    console.error(`No attribute/property:${att} found for id:${id}`);
                }
            }
        }
        else if (execution_type == 'updateStyle') {
            var id = args.id;
            var value = args.value;
            var att = args.att;
            var ele = document.getElementById(id);

            if (ele && att in ele.style) {
                ele.style[att] = value;
            }
            else {
                console.error(`No style attribute named:${att} found for id:${id}.`)
            }
        }
        else if (execution_type == 'addstyleclass') {
            HandleStyleClass(args);
        }
        else if (execution_type == 'remove') {
            var id = args.id;
            var att = args.att;
            var ele = document.getElementById(id);
            var del = deleteNestedValue(ele, att);

            if (!del) {
                if (ele && att in ele) {
                    ele.removeAttribute(att);
                }
                else {
                    console.error(`No attribute named:${att} found for id:${id}.`)
                }
            }
        }
    }

    async registerCallback(id, eventType, uuid) {
        var element = document.getElementById(id);
        const signalController = new AbortController();
        
        var wrapper = (event) => {
            // ✅ FIXED: Check explicitly for null/undefined so "", 0, and false survive
            if (event.detail !== undefined && event.detail !== null) {
                _HandleCallbackSend(uuid, this.socket, event.detail);
            }
            else {
                _HandleCallbackSend(uuid, this.socket, "");
            }
        };

        if (element) {
            element.addEventListener(eventType, wrapper, { signal: signalController.signal });
        }
        return signalController;
    }
}

function addNode(parent_id, html_to_add, mode) {
    const parentElement = document.getElementById(parent_id);
    const rawHTML = html_to_add;

    if (!parentElement) return;

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
    if (element) element.remove();
}

function addNodeHandler(msg) {
    const message = JSON.parse(msg.msg);
    addNode(message.parent_id, message.html_to_add, message.mode);
}

function remNodeHandler(msg) {
    const message = JSON.parse(msg.msg);
    remNode(message.id);
}

bind('ADD_NODE_END', addNodeHandler);
bind('REM_NODE', remNodeHandler);
// Note: Cleaned up a rogue trailing closing bracket that was here.