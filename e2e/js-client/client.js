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

const peer_id = 'peerid_js';
const py_peer_id = 'peerid_py';

function initPeer() {
    peer = new Peer(peer_id, {
        host: 'dev-peerjs.sellpath.ai',
        port: 443,
        secure: true,
        config: {
            iceServers: [
                { urls: "stun:stun.l.google.com:19302" },
                // { urls: "turn:0.peerjs.com:3478", username: "peerjs", credential: "peerjsp" }
            ]
        }
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
    console.log('Setting up connection...');
    conn.on('open', () => {
        console.log('Connection opened');
        updateStatus('Connected to Python peer');
        sendMessageButton.disabled = false;
        callButton.disabled = false;
    });

    conn.on('data', (data) => {
        console.log('Received data:', data);
        updateStatus(`Received: ${data}`);
    });

    conn.on('error', (error) => {
        console.error('Connection error:', error);
        updateStatus(`Connection error: ${error}`);
    });

    conn.on('close', () => {
        console.log('Connection closed');
        updateStatus('Connection closed');
    });
}


connectButton.addEventListener('click', () => {
    updateStatus(`Attempting to connect to peer: ${py_peer_id}`);
    console.log(`Attempting to connect to peer: ${py_peer_id}`);
    conn = peer.connect(py_peer_id, {
        reliable: true,
        serialization: 'json'
    });
    setupConnection();
});

sendMessageButton.addEventListener('click', () => {
    if (conn && conn.open) {
        conn.send('Hello from JavaScript!');
        updateStatus('Sent: Hello from JavaScript!');
    }
});


callButton.addEventListener('click', async () => {
    console.log('==========click callButton')
    if (peer) {
        try {
            console.log("==Loading audio file...");
            const audioElement = new Audio('sample-3s.mp3');
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = audioContext.createMediaElementSource(audioElement);
            const destination = audioContext.createMediaStreamDestination();
            source.connect(destination);

            console.log("==Creating audio stream from file");
            const stream = destination.stream;

            console.log("==Got audio stream from file:", stream);
            call = peer.call(py_peer_id, stream);
            
            console.log("Initiated call to Python peer");
            call.on('stream', (remoteStream) => {
                console.log("Received stream from Python peer");
                remoteAudio.srcObject = remoteStream;
                updateStatus('Voice call started');
            });

            // Start playing the audio file
            audioElement.loop = true; // Loop the audio
            audioElement.play();
        } catch (error) {
            console.error("Error initiating call:", error);
            updateStatus('Error initiating call: ' + error.message);
        }
    } else {
        console.error("==========Error click callButton  No peer yet");
    }
});

initPeer();