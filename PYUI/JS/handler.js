var SECRET_KEY = null;
var GLOBAL_CUSTOM_SYSCALL_MAP = {}; // Js object to store all the custom syscalls 


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


async function _HandleCallbackSend(uuid, socket) {
    
    //toSend = "{\"uuid\":\"" + uuid + "\",\"type\":\"CALLBACK\",\"data\":\"\"}";
    toSend = { "uuid": uuid, "type": "CALLBACK", "data": "" };

    send_str = JSON.stringify(toSend);

    //Get the sha-256 encoded string.
    sha256_encoded_msg = await standardSha256(send_str);

    //make hmac 
    hmac_code = await computeHmac(sha256_encoded_msg, SECRET_KEY);
    toSend['sign'] = hmac_code;
    GLOBAL_SOCKET.send(JSON.stringify(toSend)); //Send the msg back to python runtime
    
    
}
async function _HandleGrbContent(uuid, socket, value) {

    toSend = { "uuid": uuid, "type": "GRAB_CONTENT", "data": value };

    send_str = JSON.stringify(toSend);

    //Get the sha-256 encoded string.
    sha256_encoded_msg = await standardSha256(send_str);

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
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

async function sendSyscall(syscall, msg) {
    var call = GLOBAL_CUSTOM_SYSCALL_MAP[syscall];
    if (call) {
        var toSend = { "data": msg, "type": syscall,"uuid":generateUUID() };

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
                

            
            }
            else if (type == "UNREGISTER_CALLBACK") {
                var uuid_callback = jsonMessage.id;
                cont = this.callBackWrappers[uuid_callback];
                id = cont.Eleid;
                type = cont.type;
                wrap = cont.wrap;
                document.getElementById(id).removeEventListener(type, wrap);

                delete this.callBackWrappers[uuid_callback];
            }
            else if (type == "GRAB_CONTENT") {
                var id = jsonMessage.id;
                var attrib = jsonMessage.attrib;

                if (attrib == 'value') {
                    var value = document.getElementById(id).value;
                }
                else if (attrib == 'text') {
                    var value = document.getElementById(id).textContent;
                }

                else {
                    var value = document.getElementById(id).getAttribute(attrib);
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
            
            if(att == 'value')
            {
                document.getElementById(id).value = value; // We need to handle the value separately
            }
            else{
            var ele = document.getElementById(id);

            if (ele) {
                ele.setAttribute(att, value);
            }
        }

        }
        else if (execution_type == 'updateStyle') {

            //We need id:id , att:attribute and value:value
            var id = args.id;
            var value = args.value;
            var att = args.att;



            var js = "document.getElementById(\"" + id + "\").style." + att + " = \"" + value + "\" ;"
            eval(js);
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
        var wrapper = () => _HandleCallbackSend(uuid, this.socket);
        if (element) {
            element.addEventListener(eventType, wrapper);
        }

        return wrapper;


    }

}