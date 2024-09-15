import logging
from typing import Any, Dict, Optional
import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack
from src.enums import ConnectionType, ServerMessageType, BaseConnectionErrorType, PeerErrorType
# from .mediaconnection import MediaConnection
# from .dataconnection.DataConnection import DataConnection

logger = logging.getLogger(__name__)

class Negotiator:
    def __init__(self, connection):
        self.connection = connection

    async def start_connection(self, options: Dict[str, Any]) -> None:
        peer_connection = await self._start_peer_connection()

        self.connection.peer_connection = peer_connection

        if self.connection.type == ConnectionType.Media and options.get('_stream'):
            self._add_tracks_to_connection(options['_stream'], peer_connection)

        if options.get('originator'):
            data_connection = self.connectionx
            config = {'ordered': bool(options.get('reliable'))}

            data_channel = peer_connection.createDataChannel(
                data_connection.label,
                config
            )
            data_connection._initialize_data_channel(data_channel)

            await self._make_offer()
        else:
            await self.handle_sdp("OFFER", options['sdp'])

    async def _start_peer_connection(self):
        logger.info("Creating RTCPeerConnection.")

        peer_connection = RTCPeerConnection(
            configuration=self.connection.provider.options.get('config')
        )

        self._setup_listeners(peer_connection)

        return peer_connection

    def _setup_listeners(self, peer_connection):
        peer_id = self.connection.peer
        connection_id = self.connection.connection_id
        connection_type = self.connection.type
        provider = self.connection.provider

        logger.info("Listening for ICE candidates.")

        @peer_connection.on("icecandidate")
        def on_ice_candidate(event):
            if not event.candidate:
                return

            logger.info(f"Received ICE candidates for {peer_id}: {event.candidate}")

            provider.socket.send({
                "type": ServerMessageType.Candidate,
                "payload": {
                    "candidate": {
                        "candidate": event.candidate.candidate,
                        "sdpMid": event.candidate.sdpMid,
                        "sdpMLineIndex": event.candidate.sdpMLineIndex,
                    },
                    "type": connection_type,
                    "connectionId": connection_id,
                },
                "dst": peer_id,
            })

        @peer_connection.on("icecandidateerror")
        def on_ice_candidate_error(error):
            logger.error(f"ICE candidate error: {error}")

        @peer_connection.on("iceconnectionstatechange")
        def on_ice_connection_state_change():
            if peer_connection.iceConnectionState == "failed":
                logger.info(f"iceConnectionState is failed, closing connections to {peer_id}")
                self.connection.emit_error(
                    BaseConnectionErrorType.NegotiationFailed,
                    f"Negotiation of connection to {peer_id} failed."
                )
                self.connection.close()
            elif peer_connection.iceConnectionState == "closed":
                logger.info(f"iceConnectionState is closed, closing connections to {peer_id}")
                self.connection.emit_error(
                    BaseConnectionErrorType.ConnectionClosed,
                    f"Connection to {peer_id} closed."
                )
                self.connection.close()
            elif peer_connection.iceConnectionState == "disconnected":
                logger.info(f"iceConnectionState changed to disconnected on the connection with {peer_id}")
            elif peer_connection.iceConnectionState == "completed":
                peer_connection.on("icecandidate", lambda _: None)

            self.connection.emit(
                "iceStateChanged",
                peer_connection.iceConnectionState
            )

        logger.info("Listening for data channel")
        @peer_connection.on("datachannel")
        def on_data_channel(channel):
            logger.info("Received data channel")
            connection = provider.get_connection(peer_id, connection_id)
            connection._initialize_data_channel(channel)

        logger.info("Listening for remote stream")
        @peer_connection.on("track")
        def on_track(track):
            logger.info("Received remote stream")
            connection = provider.get_connection(peer_id, connection_id)
            if connection.type == ConnectionType.Media:
                media_connection = connection
                self._add_track_to_media_connection(track, media_connection)

    def cleanup(self) -> None:
        logger.info(f"Cleaning up PeerConnection to {self.connection.peer}")

        peer_connection = self.connection.peer_connection

        if not peer_connection:
            return

        self.connection.peer_connection = None

        # Unsubscribe from all PeerConnection's events
        peer_connection.remove_all_listeners()

        peer_connection_not_closed = peer_connection.connectionState != "closed"
        data_channel_not_closed = False

        if self.connection.data_channel:
            data_channel_not_closed = (
                self.connection.data_channel.readyState != "closed"
            )

        if peer_connection_not_closed or data_channel_not_closed:
            peer_connection.close()

    async def _make_offer(self) -> None:
        peer_connection = self.connection.peer_connection
        provider = self.connection.provider

        try:
            offer = await peer_connection.createOffer(
                **self.connection.options.get('constraints', {})
            )

            logger.info("Created offer.")

            if (
                self.connection.options.get('sdpTransform')
                and callable(self.connection.options['sdpTransform'])
            ):
                offer.sdp = self.connection.options['sdpTransform'](offer.sdp) or offer.sdp

            await peer_connection.setLocalDescription(offer)

            logger.info(
                f"Set localDescription: {offer} for: {self.connection.peer}"
            )

            payload = {
                "sdp": offer.sdp,
                "type": self.connection.type,
                "connectionId": self.connection.connection_id,
                "metadata": self.connection.metadata,
            }

            if self.connection.type == ConnectionType.Data:
                data_connection = self.connection
                payload.update({
                    "label": data_connection.label,
                    "reliable": data_connection.reliable,
                    "serialization": data_connection.serialization,
                })

            provider.socket.send({
                "type": ServerMessageType.Offer,
                "payload": payload,
                "dst": self.connection.peer,
            })
        except Exception as err:
            provider.emit_error(PeerErrorType.WebRTC, err)
            logger.error(f"Failed to create offer: {err}")

    async def _make_answer(self) -> None:
        peer_connection = self.connection.peer_connection
        provider = self.connection.provider

        try:
            answer = await peer_connection.createAnswer()
            logger.info("Created answer.")

            if (
                self.connection.options.get('sdpTransform')
                and callable(self.connection.options['sdpTransform'])
            ):
                answer.sdp = self.connection.options['sdpTransform'](answer.sdp) or answer.sdp

            await peer_connection.setLocalDescription(answer)

            logger.info(
                f"Set localDescription: {answer} for: {self.connection.peer}"
            )

            provider.socket.send({
                "type": ServerMessageType.Answer,
                "payload": {
                    "sdp": answer.sdp,
                    "type": self.connection.type,
                    "connectionId": self.connection.connection_id,
                },
                "dst": self.connection.peer,
            })
        except Exception as err:
            provider.emit_error(PeerErrorType.WebRTC, err)
            logger.error(f"Failed to create answer: {err}")

    async def handle_sdp(self, type: str, sdp: Any) -> None:
        sdp_obj = RTCSessionDescription(sdp=sdp, type=type.lower())
        peer_connection = self.connection.peer_connection
        provider = self.connection.provider

        logger.info(f"Setting remote description {sdp}")

        try:
            await peer_connection.setRemoteDescription(sdp_obj)
            logger.info(f"Set remoteDescription:{type} for:{self.connection.peer}")
            if type == "OFFER":
                await self._make_answer()
        except Exception as err:
            provider.emit_error(PeerErrorType.WebRTC, err)
            logger.error(f"Failed to set remote description: {err}")

    async def handle_candidate(self, ice: Dict[str, Any]) -> None:
        logger.info(f"handleCandidate: {ice}")

        candidate = RTCIceCandidate(
            sdpMid=ice.get('sdpMid'),
            sdpMLineIndex=ice.get('sdpMLineIndex'),
            candidate=ice.get('candidate')
        )

        try:
            await self.connection.peer_connection.addIceCandidate(candidate)
            logger.info(f"Added ICE candidate for:{self.connection.peer}")
        except Exception as err:
            self.connection.provider.emit_error(PeerErrorType.WebRTC, err)
            logger.error(f"Failed to handle ICE candidate: {err}")

    def _add_tracks_to_connection(self, stream: Any, peer_connection: RTCPeerConnection) -> None:
        logger.info(f"add tracks from stream {stream.id} to peer connection")

        for track in stream.getTracks():
            peer_connection.addTrack(track, stream)

    def _add_track_to_media_connection(self, track: MediaStreamTrack, media_connection: Any) -> None:
        logger.info(
            f"add track {track.id} to media connection {media_connection.connection_id}"
        )

        media_connection.add_track(track)