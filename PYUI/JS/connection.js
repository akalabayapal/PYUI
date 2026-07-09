
var GLOBAL_SOCKET = null;




function connectSocket(port) {

    socket = new WebSocket('ws://127.0.0.1:' + port.toString());
    GLOBAL_SOCKET = socket;
    const handler = new Msghandler(socket);


    // 2. Triggered when the handshake successfully finishes
    socket.onopen = (event) => {
        console.log('Connected to Python WebSocket Server!');
    };

    // 3. Catch and parse incoming messages from Python as JSON objects
    socket.onmessage = (event) => {



        var data = JSON.parse(event.data);
        handler.evaluateMsg(data);

    };

    socket.onclose = (event) => {
        console.warn("[PyUI Bridge] Core link severed. System may have slept. Retrying in 1.5 seconds...");
        
        // Trigger back-off retry loop
        reconnectTimer = setTimeout(() => {
            connectSocket(port);
        }, 1500);
    };

    socket.onerror = (error) => {
        console.error("[PyUI Bridge] Socket error detected:", error);
        socket.close(); // Force hit onclose handler to kick off retry loop
    };

  

}


// Enabling error on bad JS eventlisner
const originalAddEventListener = Element.prototype.addEventListener;

Element.prototype.addEventListener = function(type, callback, options) {
  const propName = 'on' + type.toLowerCase();
  
  // Warn the developer if they passed an invalid name, but ignore custom events
  if (!(propName in this)) {
    console.warn(`Warning: "${type}" might not be a valid native event for this element.`);
  }
  
  // Proceed with standard behavior anyway
  return originalAddEventListener.call(this, type, callback, options);
};



//Console log routing to main python console
console.log = function () {
    // Convert arguments to a single string
    var message = Array.from(arguments).join(' ');

    // Send to Python API
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.log(message);
    }

};

//Console log routing to main python console
console.warn = function () {
    // Convert arguments to a single string
    var message = Array.from(arguments).join(' ');

    // Send to Python API
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.warn(message);
    }

};
console.error = function () {
    // Convert arguments to a single string
    var message = Array.from(arguments).join(' ');

    // Send to Python API
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.error(message);
    }

};