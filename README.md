# peerjs-py
# peerjs-py

peerjs-py is a Python implementation of the PeerJS library, allowing peer-to-peer connections in Python applications.

## Installation

To install peerjs-py, use pip:

```
pip install peerjs-py
```


peerjs_py/
├── src/
│   ├── peerjs_python/
│   │   ├── __init__.py
│   │   ├── dataconnection/
│   │   │   ├── __init__.py
│   │   │   └── BufferedConnection/
│   │   │       ├── __init__.py
│   │   │       ├── BinaryPack.py
│   │   │       └── binaryPackChunker.py
│   │   ├── logger.py
│   │   └── enums.py
├── setup.py
├── README.md
└── requirements.txt (optional)

## Usage

### Connecting to a PeerJS Server

First, import the necessary modules and create a Peer instance:

```
python
from peerjs_python import Peer, PeerOptions
```

### Create a Peer instance
```
peer = Peer(PeerOptions(
host='your-peerjs-server.com',
port=9000,
secure=True # Use this if your server uses HTTPS
))
```
### Listen for the 'open' event to know when the connection to the server is established

```
@peer.on('open')
def on_open(id):
print(f"My peer ID is: {id}")
```

### Connecting to Another Peer

To connect to another peer and send text data:

```
#Establish a connection
conn = peer.connect('remote-peer-id')

@conn.on('open')
def on_open():
  # Connection is now open and ready for use
  conn.send('Hello, remote peer!')
@conn.on('data')
def on_data(data):
  print(f"Received: {data}")

```

### Voice/Video Calls

For voice or video calls, you'll need to use additional libraries like PyAudio for audio processing. Here's a basic example:

```
python
import pyaudio
# Initialize PyAudio
p = pyaudio.PyAudio()
# Open a call connection

call = peer.call('remote-peer-id', {'audio': True, 'video': False})

@call.on('stream')
def on_stream(stream):
  # Handle the incoming audio stream
  # This is a simplified example and would need more code to actually play the audio

@peer.on('call')
def on_call(call):
  # Answer incoming calls automatically
  call.answer({'audio': True, 'video': False})

@call.on('stream')
def on_stream(stream):
  # Handle the incoming audio stream
```


### File Transfer

To send files between peers:

```
#Sending a file
with open('file.txt', 'rb') as file:
  data = file.read()
  conn.send({'file': data, 'filename': 'file.txt'})

# Receiving a file
@conn.on('data')
def on_data(data):
  if isinstance(data, dict) and 'file' in data:
     with open(data['filename'], 'wb') as file:
       file.write(data['file'])
    print(f"Received file: {data['filename']}")

```


## Error Handling

Always implement error handling to manage potential connection issues:

```

@peer.on('error')
def on_error(error):
  print(f"An error occurred: {error}")
```

For more detailed information and advanced usage, please refer to the full documentation.

