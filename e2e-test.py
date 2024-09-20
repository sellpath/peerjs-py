import asyncio
import os
import asyncio
import sys
import json
import aiohttp
from typing import Any
from pathlib import Path

from peerjs_py.peer import Peer, PeerOptions
from peerjs_py.util import util, DEFAULT_CONFIG
from peerjs_py.enums import ConnectionEventType, PeerEventType
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
# logging.basicConfig(level=logging.DEBUG)

print(sys.version)

peer = None
savedPeerId = None
# persisted config dict

DEFAULT_LOG_LEVEL = 'DEBUG'


config = {
    "host": os.environ.get("PEERJS_HOST", "dev-peerjs.sellpath.ai"),
    "port": int(os.environ.get("PEERJS_PORT", 443)),
    "secure": os.environ.get("PEERJS_SECURE", "True").lower() == "true",
    "ice_servers": DEFAULT_CONFIG["iceServers"]
}
new_token = "new-token-1"

time_start = None
peer_connection_status = None
discoveryLoop = None
# aiohttp session reusable throghout the http proxy lifecycle
http_session = None
# flags when user requests shutdown
# via CTRL+C or another system signal
_is_shutting_down: bool = False


async def create_peer(peer_id):
    options = PeerOptions(
        host=config['host'],
        port=config['port'],
        secure=config['secure'],
        token=util.randomToken(),
        config=RTCConfiguration(
            iceServers=[RTCIceServer(**srv) for srv in config['ice_servers']]
        )
    )
    peer = Peer(id=peer_id, options=options)

    connected_event = asyncio.Event()
    open_event = asyncio.Event()

    @peer.on(PeerEventType.Disconnected.value)
    async def peer_disconnected(peer_connection):
        logger.info(f'Remote peer {peer_id} peer_disconnected')

    @peer.on(PeerEventType.Connection.value)
    async def on_connection(peer_conn):
        logger.info(f"e2e test: received connection {peer._id} from {peer_conn.peer}")

        @peer_conn.on(ConnectionEventType.Open.value)
        async def on_open():
            logger.info(f"e2e test: Connection opened on  {peer._id}  side with {peer_conn.peer}")
            open_event.set()
            await send_message(peer_conn, f"Hello from {peer._id}!")

        # @peer_conn.on(ConnectionEventType.Data.value)
        async def on_data(data):
            logger.info(f'e2e test: received {peer._id} received: {data}')
            # await send_message(peer_conn, f"Hello back from {peer._id}!")
            logger.info(f'e2e test: {peer._id} received: {data}')
            if peer._id == "peer2":
                connection = peer.get_connection(peer_conn.peer, peer_conn.connection_id)
                if connection:
                    echo_message = f"echo: {data}"
                    await send_message(connection, echo_message)
                else:
                    logger.error(f"Failed to get connection for {peer_conn.peer}")

        @peer_conn.on(ConnectionEventType.Data.value)
        def on_data_wrapper(data):
            asyncio.create_task(on_data(data))

        @peer_conn.on(ConnectionEventType.Error.value)
        def on_error(err):
            logger.error(f'e2e test: Connection error between {peer._id} and {peer_conn.peer}: {err}')

        @peer_conn.on(ConnectionEventType.Close.value)
        def on_close():
            logger.info(f'e2e test: Connection closed between {peer._id} and {peer_conn.peer}')

    @peer.on(PeerEventType.Open.value)
    async def on_open(id):
        logger.info(f"Peer {id} connected to PeerJS server")
        connected_event.set()
    
    @peer.on(PeerEventType.Error.value)
    async def on_error(error):
        logger.error(f"Peer {peer_id} encountered an error: {error}")
    
    await peer.start()

    try:
        logger.error(f"Waiting OPEN event")
        await asyncio.wait_for(connected_event.wait(), timeout=90)
    except asyncio.TimeoutError:
        logger.error(f"Peer {peer_id} failed to connect to PeerJS server")
        return None
    
    logger.info(f'Peer {peer_id} created and started')
    return peer

async def connect_peers(peer1, peer2):
    logger.info(f"e2e test: connect {peer1._id} to {peer2._id}")

    connection_opened = asyncio.Event()

    peer1_conn = await peer1.connect(peer2._id)
    if not peer1_conn:
        logger.error(f"e2e test: Failed to create connection between {peer1._id} and {peer2._id}")
        return

    # @peer1_conn.on(ConnectionEventType.Open.value)
    # async def on_open():
    #     logger.info(f"e2e test: Connection opened between {peer1._id} and {peer2._id}")
    #     connection_opened.set()

    try:
        # Wait for the connection to open
        # await asyncio.wait_for(connection_opened.wait(), timeout=120)

        # Check if the connection is open before sending a message
        if peer1_conn.open:
            connection = peer1.get_connection(peer2._id, peer1_conn.connection_id)
            if connection:
                msg =f"Hello from {peer1._id}!"
                logger.info(f"send message : {msg}")
                await connection.send(msg)
            # await send_message(peer1_conn, f"Hello from {peer1._id}!")
        else:
            logger.error(f"e2e test: Connection is not open between {peer1._id} and {peer2._id}")

        # Wait for a bit to allow messages to be exchanged
        # await asyncio.sleep(5)

        logger.info(f"e2e test: Connection test completed for {peer1._id} and {peer2._id}")
    except asyncio.TimeoutError:
        logger.error(f"e2e test: Connection timeout between {peer1._id} and {peer2._id}")
    except Exception as e:
        logger.error(f"e2e test: Error establishing connection: {str(e)}")


async def send_message(connection, message):
    logger.info(f"Attempting to send message: {message}")
    try:
        await connection.send(message)
        logger.info(f"Message sent successfully: {message}")
    except Exception as e:
        logger.error(f"Failed to send message: {e}")

async def shutdown_peers(*peers):
    for peer in peers:
        if peer:
            try:
                await peer.destroy()
            except Exception as e:
                logger.exception(f"e2e test: Error destroying peer: {e}")


async def async_main():
    try:
        logger.info('e2e test: >>>>> Starting two peers and connecting them. <<<<')
        peer1 = await create_peer("peer1")
        peer2 = await create_peer("peer2")
        
        # logger.info('e2e test: wait 2 sec')
        # await asyncio.sleep(2)
        # Connect peer1 to peer2
        await connect_peers(peer1, peer2)
        
        # Keep the program running for a while to allow for message exchange
        await asyncio.sleep(5)
    except KeyboardInterrupt:
        logger.info('e2e test: KeyboardInterrupt detected.')
    except Exception as e:
        logger.exception(f'e2e test: An unexpected error occurred: {e}')
    finally:
        logger.info('e2e test: Shutting down...')
        await shutdown_peers(peer1, peer2)
        logger.info('e2e test: All done.')

@logger.catch
def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()