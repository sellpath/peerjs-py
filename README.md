# peerjs-py

peerjs-py is a Python implementation of the PeerJS library, allowing peer-to-peer connections in Python applications.

## Installation

To install peerjs-py, use pip:

```
pip install peerjs-py
```

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

## Testing

To ensure the reliability and functionality of peerjs-py, we have implemented a comprehensive testing suite. Before running the tests, please note that you must have your own PeerJS signaling server set up.

### Running Tests

We use pytest as our testing framework. To run the tests, follow these steps:

1. Ensure you have pytest installed:
   ```
   pip install pytest
   ```

2. Navigate to the project root directory.

3. Run the tests using pytest:
   ```
   pytest
   ```

### End-to-End Tests

We have two types of end-to-end (e2e) tests to verify the functionality of peerjs-py in different scenarios:

1. **Python Client to Python Client Test**
   This test checks the communication between two Python clients using peerjs-py.
   
   To run this test:
   ```
   ./e2e/run-e2e.sh
   ```

2. **PeerJS Browser Client to Python Client Test**
   This test verifies the compatibility between a PeerJS browser client and a Python client using peerjs-py.
   
   To run this test:
   ```
   ./e2e/run-e2e-test-py.sh
   ```

### Important Notes

- Ensure your PeerJS signaling server is running and accessible before executing the tests.
- The end-to-end tests may require additional setup or dependencies. Please refer to the respective script files for any specific instructions.
- If you encounter any issues during testing, check your server configuration and network connectivity.

By running these tests, you can verify that peerjs-py is working correctly in various scenarios and is compatible with both Python-to-Python and Browser-to-Python communications.