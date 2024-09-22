import asyncio
from aiohttp import web
import socketio
from peerjs_py import Peer
import argparse

# Create a new Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins='*')

# Create a new Aiohttp Web Application
app = web.Application()
sio.attach(app)

@sio.event
async def connect(sid, environ):
    peer = Peer()
    await peer.start()
    await sio.emit('peer_id', peer.id, room=sid)

async def init_app():
    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run PeerJS server')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()

    web.run_app(app, host='localhost', port=args.port)