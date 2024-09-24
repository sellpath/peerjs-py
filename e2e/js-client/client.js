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

const DEFAULT_MY_PEER_ID = 'peerid_js';
const DEFAULT_PY_PEER_ID = 'peerid_py';

function getMyPeerId() {
    const input = document.getElementById('mypeerIdInput');
    return input && input.value.trim() || DEFAULT_MY_PEER_ID;
}
function getPyPeerId() {
    const input = document.getElementById('peerIdInput');
    return input && input.value.trim() || DEFAULT_PY_PEER_ID;
}

// Add this new function
function reinitializePeer() {
    if (peer) {
        peer.destroy();
    }
    initPeer();
}

function initPeer() {
    const myPeerId = getMyPeerId();
    peer = new Peer(myPeerId, {
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
            remoteAudio.src = URL.createObjectURL(remoteStream);
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
    const pyPeerId = getPyPeerId();

    updateStatus(`Attempting to connect to connect ${pyPeerId}`);
    console.log(`Attempting to connect to connect ${pyPeerId}`);
    conn = peer.connect(pyPeerId, {
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
    const pyPeerId = getPyPeerId();
    console.log('==========click callButton')
    if (peer) {
        try {
            console.log("==Loading audio...");
            let stream;
            const useBrowserAudio = document.getElementById('useBrowserAudio').checked;

            if (useBrowserAudio) {
                console.log("==Using browser audio");
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            } else {
                console.log("==Using local audio file");
                const audioElement = new Audio('sample-3s.mp3');
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const source = audioContext.createMediaElementSource(audioElement);
                const destination = audioContext.createMediaStreamDestination();
                source.connect(destination);
                stream = destination.stream;
            }

            console.log(`==Initiating call to Python peer  call ${pyPeerId}`);
            call = peer.call(pyPeerId, stream);
            
            call.on('stream', (remoteStream) => {
                console.log("Received stream from Python peer:", remoteStream);
                console.log("Stream type:", remoteStream.constructor.name);
                console.log("Stream has audio tracks:", remoteStream.getAudioTracks().length > 0);
                
                remoteAudio.srcObject = remoteStream;
                updateStatus('Voice call connected');

                // Save the received audio
                const mediaRecorder = new MediaRecorder(remoteStream);
                const chunks = [];

                mediaRecorder.ondataavailable = (event) => {
                    updateStatus('Voice call connected: mediaRecorder ondataavailable');
                    if (event.data.size > 0) {
                        chunks.push(event.data);
                    }
                };

                mediaRecorder.onstop = () => {
                    updateStatus('Voice call connected: mediaRecorder onstop');
                    const blob = new Blob(chunks, { type: 'audio/wav' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'received_audio.wav';
                    document.body.appendChild(a);
                    a.click();
                    setTimeout(() => {
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);
                        updateStatus('Audio playback completed');
                    }, 100);
                };

                mediaRecorder.start();

                const useBrowserAudio = document.getElementById('useBrowserAudio').checked;
                let recordingDuration = useBrowserAudio ? 5000 : 3000; // 10 seconds for browser audio, 3 seconds for local file
            
                // Stop recording after 2 seconds (adjust as needed)
                setTimeout(() => {
                    updateStatus('Voice call connected: mediaRecorder stop done');
                    mediaRecorder.stop();
                }, recordingDuration);
            });

            // Wait for the call to be established
            if (!useBrowserAudio) {
                console.log(`==Call established, starting audio playback  call ${pyPeerId}`);
                updateStatus('Sending audio...');
                
                // Start playing the audio file (this is when it actually starts sending)
                audioElement.loop = false;
                await audioElement.play();

                // Wait for the audio to finish playing
                await new Promise(resolve => {
                    audioElement.onended = resolve;
                });

                console.log("Audio finished playing");
                updateStatus('Audio playback completed');

                // Clean up audio resources
                source.disconnect();
                audioContext.close();
            }

            updateStatus('Audio playback completed');

        } catch (error) {
            console.error("Error during call:", error);
            updateStatus('Error during call: ' + error.message);
        }
    } else {
        console.error("==========Error click callButton  No peer yet");
    }
});

document.getElementById('mypeerIdInput').addEventListener('change', reinitializePeer);

initPeer();