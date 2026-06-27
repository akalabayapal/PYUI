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




//Console log routing to main python console
console.log = function () {
    // Convert arguments to a single string
    var message = Array.from(arguments).join(' ');

    // Send to Python API
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.log(message);
    }

};