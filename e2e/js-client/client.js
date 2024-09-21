let peer;
let conn;
let call;

const statusElement = document.getElementById('status');
const connectButton = document.getElementById('connect');
const sendMessageButton = document.getElementById('sendMessage');
const callButton = document.getElementById('call');
const remoteAudio = document.getElementById('remoteAudio');

function updateStatus(message) {
    statusElement.textContent = message;
}

function initPeer() {
    peer = new Peer(undefined, {
        host: 'localhost',
        port: 5000,
        path: '/peerjs'
    });


    peer.on('open', (id) => {
        console.log(`Peer opened with ID: ${id}`);
        updateStatus(`My peer ID is: ${id}`);
        connectButton.disabled = false;
    });

    peer.on('error', (error) => {
        console.error('Peer error:', error);
        updateStatus(`Peer error: ${error.type}`);
    });

    peer.on('connection', (connection) => {
        conn = connection;
        setupConnection();
    });

    peer.on('call', (incomingCall) => {
        call = incomingCall;
        call.answer();
        call.on('stream', (remoteStream) => {
            remoteAudio.srcObject = remoteStream;
        });
    });
}

function updateStatus(message) {
    console.log('Status update:', message);
    statusElement.textContent = message;
}

function setupConnection() {
    conn.on('open', () => {
        updateStatus('Connected to Python peer');
        sendMessageButton.disabled = false;
        callButton.disabled = false;
    });

    conn.on('data', (data) => {
        updateStatus(`Received: ${data}`);
    });
}

connectButton.addEventListener('click', () => {
    conn = peer.connect('python-peer-id');
    setupConnection();
});

sendMessageButton.addEventListener('click', () => {
    if (conn && conn.open) {
        conn.send('Hello from JavaScript!');
        updateStatus('Sent: Hello from JavaScript!');
    }
});

callButton.addEventListener('click', async () => {
    if (peer) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        call = peer.call('python-peer-id', stream);
        call.on('stream', (remoteStream) => {
            remoteAudio.srcObject = remoteStream;
        });
        updateStatus('Voice call started');
    }
});

initPeer();