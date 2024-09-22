from typing import Any, Dict, Optional, Union, List
import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack, RTCDataChannel

from aiortc.sdp import candidate_from_sdp, candidate_to_sdp
from peerjs_py.enums import ConnectionType, ServerMessageType, BaseConnectionErrorType, PeerErrorType
from peerjs_py.logger import logger
import logging
# from .mediaconnection import MediaConnection
# from .dataconnection.DataConnection import DataConnection

class Negotiator:
    def __init__(self, connection):
        self.connection = connection
        self.ice_gathering_complete = asyncio.Event()
        self.local_description_set = asyncio.Event()
        self.offer_answer_sent = False
        self.connection_established = False

    async def start_connection(self, options: Dict[str, Any]) -> None:
        logger.info(f"Starting connection for {self.connection.connection_id}")
        peer_connection:RTCPeerConnection = await self._start_peer_connection()
        self.connection.peer_connection = peer_connection

        connection_id = options.get('connectionId') or self.connection.connection_id
        logger.debug(f"connectionId set: options connectionId: {connection_id} vs self.connection.connection_id: {self.connection.connection_id}")
        self.connection.connection_id = connection_id

        if self.connection.type == ConnectionType.Media and options.get('_stream'):
            logger.info(f"Adding tracks to connection for {self.connection.connection_id}")
            self._add_tracks_to_connection(options['_stream'], peer_connection)

        logger.debug(f"start_connection => options: {options}")
        if options.get('originator'):
            if not self.connection.data_channel:
                logger.info(f"Creating data channel for {self.connection.connection_id}")
                data_channel:RTCDataChannel = peer_connection.createDataChannel(
                    label=connection_id, #self.connection.connection_id,
                    ordered=options.get("reliable", True),
                    protocol=options.get("protocol", ""),
                    # negotiated=False,
                )
                logger.debug(f"start_connection try connection._initialize_data_channel options: {data_channel}")
                await self.connection._initialize_data_channel(data_channel)

            logger.info(f"Making offer for {self.connection.connection_id}")
            await self._make_offer()
            logger.info(f"Offer made for {self.connection.connection_id}")
            # The actual sending of the offer will be triggered by the icegatheringstatechange event
        else:
            logger.info(f"Handling SDP for {self.connection.connection_id}")
            await self.handle_sdp("OFFER", options['sdp'])

    async def _start_peer_connection(self):
        logger.info(f"Creating RTCPeerConnection. config: {self.connection.provider._options.get('config')}")
 # Check if there's an existing peer connection
        if self.connection.peer_connection:
            if self.connection.peer_connection.connectionState in ['closed', 'failed']:
                logger.info("Existing peer connection is closed or failed. Creating a new one.")
            else:
                logger.warning("Attempting to create a new peer connection while an active one exists.")
                return self.connection.peer_connection
            
        logger.info("Creating a new peer_connection RTCPeerConnection ")
        peer_connection: RTCPeerConnection = RTCPeerConnection(
            configuration=self.connection.provider._options.get('config')
        )
        if peer_connection.connectionState in ['closed', 'failed']:
            logger.info("new peer_connection peer connection is closed or failed: {peer_connection.connectionState }")
        else:
            logger.info(f"new peer_connection peer connection state: {peer_connection.connectionState }")

        self._setup_listeners(peer_connection)

        return peer_connection


    async def on_data_channel(self, channel):
        peer_id = self.connection.peer
        connection_id = self.connection.connection_id
        provider = self.connection.provider
        logger.info(f"Received data channel: for self.connection.connection_id: {self.connection.connection_id}")
        connection = provider.get_connection(peer_id, connection_id)
        if connection:
            await connection._initialize_data_channel(channel)
        else:
            logger.info(f"datachannel event failed to get connect from peer_id:{peer_id} connection_id:{connection_id}")

            # await self.connection._initialize_data_channel(channel)
        @channel.on("open")
        def on_channel_open():
            logger.info(f"on_data_channel Data channel '{channel.label}' opened")

        @channel.on("close")
        def on_channel_close():
            logger.info(f"on_data_channel Data channel '{channel.label}' closed")

        @channel.on("error")
        def on_channel_error(error):
            logger.error(f"on_data_channel Data channel '{channel.label}' error: {error}")


    def _setup_listeners(self, peer_connection: RTCPeerConnection):
        peer_id = self.connection.peer
        connection_id = self.connection.connection_id
        connection_type = self.connection.type
        provider = self.connection.provider

        logger.info("Listening for data channel iceconnectionstatechange")
        @peer_connection.on("iceconnectionstatechange")
        async def on_ice_connection_state_change():
            if peer_connection.iceConnectionState in ["failed", "closed", "disconnected"]:
                logger.info(f"iceConnectionState is {peer_connection.iceConnectionState}, closing connections to {peer_id}")
                await self.connection.close()
            elif peer_connection.iceConnectionState == "completed":
                logger.info(f"ICE connection completed with {peer_id}")

            self.connection.emit(
                "iceStateChanged",
                peer_connection.iceConnectionState
            )

        logger.info("Listening for data channel")
        @peer_connection.on("datachannel")
        def on_data_channel_wrapper(channel):
            asyncio.create_task( self.on_data_channel(channel))

        logger.info("Listening for remote stream")
        @peer_connection.on("track")
        def on_track(track: MediaStreamTrack):
            logger.info(f"Received remote track: {track.kind}")
            
            provider = self.connection.provider
            connection = provider.get_connection(peer_id, connection_id)
            if not connection:
                logger.error(f"track event failed to get connection from peer_id:{peer_id} connection_id:{connection_id}")
                return
            
            if connection.type == ConnectionType.Media:
                media_connection = connection
                self._handle_track_for_media_connection(track, media_connection)
            else:
                logger.error(f"Unexpected connection type for track event: peer_id:{peer_id} connection_id:{connection_id}")


        @peer_connection.on("signalingstatechange")
        def on_signaling_state_change():
            logger.info(f"Signaling state changed to: {peer_connection.signalingState} peer_id:{peer_id}")
            self.connection.emit("signalingStateChanged", peer_connection.signalingState)

        @peer_connection.on("connectionstatechange")
        async def on_connection_state_change():
            logger.info(f"Connection state changed to: {peer_connection.connectionState} peer_id:{peer_id}")
            if peer_connection.connectionState == "failed":
                await peer_connection.close()
                # pcs.discard(pc)
            self.connection.emit("connectionStateChanged", peer_connection.connectionState)

        @peer_connection.on("icegatheringstatechange")
        def on_ice_gathering_state_change():
            logger.info(f"ICE gathering state changed to: {peer_connection.iceGatheringState} peer_id:{self.connection.peer}")
            self.connection.emit("iceGatheringStateChanged", peer_connection.iceGatheringState)
            if peer_connection.iceGatheringState == "complete":
                self.ice_gathering_complete.set()
                asyncio.create_task(self._try_send_offer_or_answer())

    async def cleanup(self) -> None:
        logger.info(f"Cleaning up PeerConnection to {self.connection.peer}")

        peer_connection = self.connection.peer_connection

        if not peer_connection:
            return

        self.connection.peer_connection = None

        # Unsubscribe from all PeerConnection's events
        async def remove_listener(event_name):
            if asyncio.iscoroutinefunction(peer_connection.on):
                await peer_connection.on(event_name, None)
            else:
                peer_connection.on(event_name, None)

        await remove_listener("icecandidate")
        # await remove_listener("icecandidateerror")
        await remove_listener("iceconnectionstatechange")
        await remove_listener("datachannel")
        await remove_listener("track")
        await remove_listener("signalingstatechange")
        await remove_listener("connectionstatechange")
        await remove_listener("icegatheringstatechange")

        peer_connection_not_closed = peer_connection.connectionState != "closed"
        data_channel_not_closed = False

        if self.connection.data_channel:
            data_channel_not_closed = (
                self.connection.data_channel.readyState != "closed"
            )

        if peer_connection_not_closed or data_channel_not_closed:
            await peer_connection.close() # RTCPeerConnection.close

    async def _make_offer(self) -> None:
        logger.debug("_make_offer: start")

        peer_connection: RTCPeerConnection = self.connection.peer_connection
        provider = self.connection.provider

        try:
            logger.info("_make_offer: Attempting to create offer.")
            logger.info(f"RTCPeerConnection config: {self.connection.provider._options.get('config')}")
            offer = await peer_connection.createOffer(
                **self.connection.options.get('constraints', {})
            )

            logger.info("_make_offer: Offer created successfully.")
            logger.debug(f"Offer SDP: {offer.sdp}")

            if (
                self.connection.options.get('sdpTransform')
                and callable(self.connection.options['sdpTransform'])
            ):
                offer.sdp = self.connection.options['sdpTransform'](offer.sdp) or offer.sdp

            logger.info("Attempting to set local description.")
            await peer_connection.setLocalDescription(offer)
            self.local_description_set.set()
            logger.info(f"Set localDescription: {offer} for: {self.connection.peer}")

            await self._try_send_offer_or_answer()

            # The actual sending of the offer will be triggered by the icegatheringstatechange event
        except Exception as err:
            logger.exception(f"_make_offer: Failed to create offer: {err}")
            await provider.emit_error(PeerErrorType.WebRTC.value, err)

    async def _make_answer(self):
        logger.info("Creating answer")
        answer = await self.connection.peer_connection.createAnswer()
        await self.connection.peer_connection.setLocalDescription(answer)
        self.local_description_set.set()
        logger.info("Local description set for ANSWER")
        # The actual sending of the answer will be triggered by the icegatheringstatechange event

        await self._try_send_offer_or_answer()

    
    async def _try_send_offer_or_answer(self):
        if self.offer_answer_sent:
            return

        await asyncio.gather(self.local_description_set.wait(), self.ice_gathering_complete.wait())
        
        if not self.offer_answer_sent:
            self.offer_answer_sent = True
            await self._send_offer_or_answer()

    async def _send_offer_or_answer(self):
        if self.connection_established:
            logger.info("_send_offer_or_answer: Connection already established, not sending offer/answer")
            return
        
        peer_connection: RTCPeerConnection = self.connection.peer_connection
        provider = self.connection.provider

        local_description = peer_connection.localDescription
        if not local_description:
            logger.error("No local description available to send")
            return

        sdp_message = {
            "sdp": local_description.sdp,
            "type": local_description.type
        }

        payload = {
            "sdp": sdp_message, #local_description.sdp,
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

        message_type = ServerMessageType.Offer if local_description.type == "offer" else ServerMessageType.Answer
        logger.info(f"_send_offer_or_answer Sending {message_type.value} with payload: {payload}")
        
        await provider._socket.send({
            "type": message_type.value,
            "payload": payload,
            "dst": self.connection.peer,
        })

    async def handle_sdp(self, type_, sdp):
        logger.info(f"Negotiator handling SDP: {type_}")
        peer_connection = self.connection.peer_connection
        provider = self.connection.provider

        if self.connection_established:
            logger.info(f"Ignoring {type_} as connection is already established")
            return
            
        logger.debug(f"Received SDP: {sdp}")
        logger.debug(f"SDP type: {type(sdp)}")

        if type_ == ServerMessageType.Offer.value:
            if peer_connection.signalingState != "stable":
                logger.warning("Ignoring offer in non-stable state")
                return
            try:
                sdp_string = sdp['sdp']
                sdp_type = sdp['type'].lower()
                sdp_obj = RTCSessionDescription(sdp=sdp_string, type=sdp_type)
                await peer_connection.setRemoteDescription(sdp_obj)
                logger.info(f"Set remoteDescription:{type_} for:{self.connection.peer}")
                await self._make_answer()
                # The actual sending of the answer will be triggered by the icegatheringstatechange event
            except Exception as err:
                logger.exception(f"handle_sdp:  ServerMessageType.Offer Failed to set remote description: {err}")
                await provider.emit_error(PeerErrorType.WebRT.value, err)
            
        elif type_ == ServerMessageType.Answer.value:
            if peer_connection.signalingState != "have-local-offer":
                logger.warning(f"Ignoring answer in {peer_connection.signalingState} state")
                return
            try:
                sdp_string = sdp['sdp']
                sdp_type = sdp['type'].lower()
                sdp_obj = RTCSessionDescription(sdp=sdp_string, type=sdp_type)
                await peer_connection.setRemoteDescription(sdp_obj)
                logger.info(f"Remote description set for {type_} from peer {self.connection.peer}")
                self.connection_established = True
            except Exception as err:
                logger.error(f"handle_sdp: ServerMessageType.Answer Failed to set remote description: {err}")
                await provider.emit_error(PeerErrorType.WebRTC.value, err)

        else:
            logger.warning(f"Unsupported SDP type: {type_}")

    async def handle_candidate(self, ice: Dict[str, Any]) -> None:
        logger.debug(f"handle_candidate Handling ICE candidate: {ice}")

        try:
            rtc_ice_candidate = candidate_from_sdp(ice['candidate'])
            rtc_ice_candidate.sdpMid = ice.get('sdpMid')
            rtc_ice_candidate.sdpMLineIndex = ice.get('sdpMLineIndex')

            logger.debug(f"Created RTCIceCandidate: {rtc_ice_candidate}")
            logger.debug(f"PeerConnection: {self.connection.peer_connection}")

            await self.connection.peer_connection.addIceCandidate(rtc_ice_candidate)
            logger.info(f"Added ICE candidate for peer: {self.connection.peer}")
        except Exception as err:
            await self.connection.provider.emit_error(PeerErrorType.WebRTC, err)
            logger.exception(f"Failed to handle ICE candidate: {err}")

    def _add_tracks_to_connection(self, stream: Union[Any, List[MediaStreamTrack]], peer_connection: RTCPeerConnection) -> None:
        if isinstance(stream, list):
            # If stream is already a list of tracks
            tracks = stream
        elif hasattr(stream, 'getTracks'):
            # If stream has getTracks method (like MediaStream)
            tracks = stream.getTracks()
        elif isinstance(stream, MediaStreamTrack):
            # If stream is a single track
            tracks = [stream]
        else:
            logger.warning(f"Unsupported stream type: {type(stream)}. Unable to add tracks.")
            return
        
        stream_id = getattr(stream, 'id', 'unknown')
        logger.info(f"Adding {len(tracks)} track(s) from stream {stream_id} to peer connection")

        for track in tracks:
            peer_connection.addTrack(track)


    def _handle_track_for_media_connection(self, track: MediaStreamTrack, media_connection: Any) -> None:
        logger.info(
            f"Handling track {track.id} of kind {track.kind} for media connection {media_connection.connection_id}"
        )

        # Instead of calling add_track, emit an event or update the MediaConnection's state
        # This depends on how your MediaConnection class is implemented

        # if hasattr(media_connection, 'emit'):
        #     media_connection.emit('track', track)
        #     media_connection.emit('stream', media_connection._remote_stream)
        # el
        if hasattr(media_connection, 'on_track'):
            media_connection.on_track(track)
        else:
            logger.warning(f"Unable to handle track for media connection {media_connection.connection_id}. No suitable method found.")

        # If MediaConnection has a tracks attribute, you might want to append the track
        if hasattr(media_connection, 'tracks'):
            media_connection.tracks.append(track)
        
        asyncio.create_task(media_connection._handle_track(track))


    # not in use 
    # def _add_track_to_media_connection(self, track: MediaStreamTrack, media_connection: Any) -> None:
    #     logger.info(
    #         f"add track {track.id} of kind {track.kind} to media connection {media_connection.connection_id}"
    #     )

    #     media_connection.add_track(track)

    # not with aiortc  use _add_track_to_media_connection
    # def _add_stream_to_media_connection(self, stream: MediaStream, media_connection: Any) -> None:
    #     logger.info(
    #         f"add stream {stream.id} to media connection {media_connection.connection_id}"
    #     )

    #     media_connection.add_stream(stream)