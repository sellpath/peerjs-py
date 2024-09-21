import asyncio
from peerjs_py import Peer, PeerOptions
from peerjs_py.enums import ConnectionEventType, PeerEventType
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRecorder
from peerjs_py.util import util, DEFAULT_CONFIG
from aiortc.rtcconfiguration import RTCConfiguration, RTCIceServer
import logging
from peerjs_py.logger import logger, LogLevel

logger.set_log_level(LogLevel.All)

aiortc_logger = logging.getLogger("aiortc")
aiortc_logger.setLevel(logging.DEBUG)
aiortc_logge_pc = logging.getLogger("pc")
aiortc_logge_pc.setLevel(logging.DEBUG)
aiortc_logge_datachannel = logging.getLogger("datachannel")
aiortc_logge_datachannel.setLevel(logging.DEBUG)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

peer_id = "peerid_py"
js_peer_id = "peerid_js"
connection = None
recorder = None

async def handle_connection(conn, peer):
    global connection
    connection = conn
    logger.info(f"Handling connection from: {conn.peer}")
    logger.info(f"Connection object: {conn}")
    logger.info(f"Current connections before adding: {peer._connections}")

    @conn.on(ConnectionEventType.Open.value)
    async def on_open():
        logger.info(f"Connection opened with: {conn.peer}")
        print(f"Connection opened with: {conn.peer}")
        try:
            await send_message(conn, "Hello from Python!")
        except Exception as e:
            logger.error(f"Error sending initial message: {e}")
            print(f"Error sending initial message: {e}")

    async def on_data(data):
        logger.info(f"Received data: {data}")
        print(f"Received data: {data}")
        await send_message(conn, f"Echo: {data}")

    @conn.on(ConnectionEventType.Data.value)
    def on_data_wrapper(data):
        asyncio.create_task(on_data(data))

    @conn.on(ConnectionEventType.Close.value)
    async def on_close():
        logger.info(f"Connection closed with: {conn.peer}")
        print(f"Connection closed with: {conn.peer}")

    @conn.on(ConnectionEventType.Error.value)
    async def on_error(error):
        logger.error(f"Connection error: {error}")
        print(f"Connection error: {error}")

async def handle_call(call):
    global recorder
    print(f"Handling incoming call from {call.peer}")

    @call.on("stream")
    async def on_stream(stream):
        print(f"Received stream from {call.peer}")
        try:
            recorder = MediaRecorder("received_audio.wav")
            recorder.addTrack(stream.getAudioTracks()[0])
            await recorder.start()
            print("Started recording")
            await asyncio.sleep(5)  # Record for 5 seconds
            await recorder.stop()
            print("Stopped recording")
            print("Voice call completed and audio saved")
        except Exception as e:
            print(f"Error during call handling: {e}")

    try:
        audio = MediaPlayer("../tests/sample-3s.mp3")
        if not audio or not audio.audio:
            print("Error: MediaPlayer failed to load audio")
            return
        print("Answering call with audio")
        await call.answer(audio.audio)
        print("Call answered successfully")
    except Exception as e:
        print(f"Error answering call: {e}")

async def send_message(connection, message):
    logger.info(f"Attempting to send message: {message}")
    try:
        await connection.send(message)
        logger.info(f"Message sent successfully: {message}")
    except Exception as e:
        logger.error(f"Failed to send message: {e}")

async def main():
    config = {
        "host": "dev-peerjs.sellpath.ai",
        "port": 443,
        "secure": True,
        "ice_servers": DEFAULT_CONFIG["iceServers"]
    }
    options = PeerOptions(
        host=config['host'],
        port=config['port'],
        secure=config['secure'],
        config=RTCConfiguration(
            iceServers=[RTCIceServer(**srv) for srv in config['ice_servers']]
        )
    )
    peer = Peer(peer_id, options)

    @peer.on(PeerEventType.Open.value)
    def on_open(peerid):
        logger.info(f"Peer opened with ID: {peer_id} peerid: {peerid}")
        print(f"Peer open with ID: {peer_id}")

    @peer.on(PeerEventType.Connection.value)
    async def on_connection(conn):
        logger.info(f"Received connection from: {conn.peer}")
        print(f"Received connection from: {conn.peer}")
        try:
            await handle_connection(conn, peer)
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
            print(f"Error handling connection: {e}")

    @peer.on(PeerEventType.Call.value)
    async def on_call(call):
        logger.info(f"Received call from: {call.peer}")
        await handle_call(call)

    @peer.on(PeerEventType.Error.value)
    def on_error(error):
        logger.error(f"Peer error: {error}")
        print(f"Peer error: {error}")

    try:
        logger.info(f"Starting peer with ID: {peer_id}")
        await peer.start()
        logger.info(f"Peer started successfully with ID: {peer.id}")
        print(f"Peer started successfully with ID: {peer.id}")
    except Exception as e:
        logger.error(f"Failed to start peer: {e}")
        print(f"Failed to start peer: {e}")
        return

    # Keep the script running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())