from typing import Any, Callable, Optional

class AnswerOption:
    sdp_transform: Optional[Callable] = None

class PeerJSOption:
    key: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    path: Optional[str] = None
    secure: Optional[bool] = None
    token: Optional[str] = None
    config: Optional[dict] = None  # Equivalent to RTCConfiguration
    debug: Optional[int] = None
    referrer_policy: Optional[str] = None  # Equivalent to ReferrerPolicy

class PeerConnectOption:
    label: Optional[str] = None
    metadata: Any = None
    serialization: Optional[str] = None
    reliable: Optional[bool] = None

class CallOption:
    metadata: Any = None
    sdp_transform: Optional[Callable] = None