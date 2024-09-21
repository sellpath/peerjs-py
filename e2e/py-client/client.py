import asyncio
from peerjs_py import Peer, PeerOptions
from peerjs_py.enums import ConnectionEventType, PeerEventType
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRecorder

peer_id = "python-peer-id"
js_peer_id = None
connection = None
recorder = None

async def handle_connection(conn):
    global connection
    connection = conn

    @connection.on(ConnectionEventType.Data)
    async def on_data(data):
        print(f"Received data: {data}")
        await connection.send("Hello from Python!")

async def handle_call(call):
    global recorder

    @call.on("stream")
    async def on_stream(stream):
        print("Received stream from JavaScript peer")
        recorder = MediaRecorder("received_audio.wav")
        recorder.addTrack(stream.getAudioTracks()[0])
        await recorder.start()
        await asyncio.sleep(5)  # Record for 5 seconds
        await recorder.stop()
        print("Voice call completed and audio saved")

    audio = MediaPlayer("../tests/sample-3s.mp3")
    await call.answer(audio.audio)

async def main():
    peer = Peer(peer_id, PeerOptions(host="localhost", port=5000, secure=False))

    @peer.on(PeerEventType.Open)
    def on_open():
        print(f"Peer open with ID: {peer_id}")

    @peer.on(PeerEventType.Connection)
    async def on_connection(conn):
        await handle_connection(conn)

    @peer.on(PeerEventType.Call)
    async def on_call(call):
        await handle_call(call)

    await peer.start()
    
    # Keep the script running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())