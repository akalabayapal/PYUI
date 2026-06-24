class PriorityQueue {
    constructor(initialCapacity = 100) {
        this.capacity = initialCapacity;
        this.heap = new Array(this.capacity);
        this.size = 0;
    }

    // Insert a new object and check for resize
    enqueue(priority, obj) {
        // 1. Check if we need to resize before adding
        if (this.size === this.capacity) {
            this.resize();
        }

        // 2. Insert at the end of the heap
        const newNode = { priority, object: obj };
        this.heap[this.size] = newNode;

        // 3. Heapify Up to restore min-heap property
        this.heapifyUp(this.size);
        this.size++;
    }

    // Remove and return the highest priority item (lowest priority number)
    dequeue() {
        if (this.size === 0) return null;

        const root = this.heap[0];
        const lastNode = this.heap[this.size - 1];

        // Move the last element to the root
        this.heap[0] = lastNode;
        this.heap[this.size - 1] = null; // Clear reference for garbage collection
        this.size--;

        // Heapify Down to restore min-heap property
        if (this.size > 0) {
            this.heapifyDown(0);
        }

        return root;
    }

    // Double the array capacity when full
    resize() {
        this.capacity *= 2;
        const newHeap = new Array(this.capacity);

        // Copy elements over
        for (let i = 0; i < this.size; i++) {
            newHeap[i] = this.heap[i];
        }

        this.heap = newHeap;
        console.log(`[PriorityQueue] Resized. New capacity: ${this.capacity}`);
    }

    // Restores heap order going up
    heapifyUp(index) {
        while (index > 0) {
            const parentIndex = Math.floor((index - 1) / 2);

            // If current node's priority is fine, break
            if (this.heap[index].priority >= this.heap[parentIndex].priority) {
                break;
            }

            this.swap(index, parentIndex);
            index = parentIndex;
        }
    }

    // Restores heap order going down
    heapifyDown(index) {
        while (2 * index + 1 < this.size) {
            let smallestChildIndex = 2 * index + 1; // Assume left child is smaller
            const rightChildIndex = 2 * index + 2;

            // Check if right child exists and has a lower priority number
            if (
                rightChildIndex < this.size &&
                this.heap[rightChildIndex].priority < this.heap[smallestChildIndex].priority
            ) {
                smallestChildIndex = rightChildIndex;
            }

            // If parent is already smaller than the smallest child, we are done
            if (this.heap[index].priority <= this.heap[smallestChildIndex].priority) {
                break;
            }

            this.swap(index, smallestChildIndex);
            index = smallestChildIndex;
        }
    }

    // Helper to swap two nodes in the array
    swap(i, j) {
        const temp = this.heap[i];
        this.heap[i] = this.heap[j];
        this.heap[j] = temp;
    }

    peek() {
        return this.size > 0 ? this.heap[0] : null;
    }

    isEmpty() {
        return this.size === 0;
    }
}





var GLOBAL_SOCKET = null;




function connectSocket(port) {

    socket = new WebSocket('ws://127.0.0.1:' + port.toString());
    GLOBAL_SOCKET = socket;
    const handler = new Msghandler(socket);
    const priority_queue = new PriorityQueue(1000);


    // 2. Triggered when the handshake successfully finishes
    socket.onopen = (event) => {
        console.log('Connected to Python WebSocket Server!');
    };

    // 3. Catch and parse incoming messages from Python as JSON objects
    socket.onmessage = (event) => {

        var data = JSON.parse(event.data);
        if (data.type == "BATCH_UPDATE") {
            handler.evaluateMsg(data);
        }
        else {
            priority_queue.enqueue(data.count, data);
        }
        


    };

    let nextExpectedSequence = 0;
    //Run loop to dequeue the object and get the object
    setInterval(() => {

        while (!priority_queue.isEmpty()) {
            const topItem = priority_queue.peek(); // Just look, don't remove yet!

            // If the top item is exactly what we are waiting for, process it!
            if (topItem.priority === nextExpectedSequence) {
                const msg = priority_queue.dequeue();

                handler.evaluateMsg(msg.object); // Run your UI framework logic here

                nextExpectedSequence++; // Move to the next expected number
            } else {
                // The next message hasn't arrived from Python yet (there's a gap).
                // Stop processing and wait for the network/socket to catch up!
                break;
            }
        }

    }, 16);

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