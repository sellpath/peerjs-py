import sys
import platform
import aiortc

class Supports:
    def __init__(self):
        self.is_ios = platform.system() == "Darwin" and platform.machine().startswith("iP")
        self.supported_platforms = ["Linux", "Darwin", "Windows"]
        self.min_python_version = (3, 7)

    def is_webrtc_supported(self):
        return 'aiortc' in sys.modules

    def is_platform_supported(self):
        return platform.system() in self.supported_platforms and sys.version_info >= self.min_python_version

    def get_platform(self):
        return platform.system()

    def get_version(self):
        return sys.version_info
    
    def get_browser(self):
        return platform.system()

    def is_unified_plan_supported(self):
        return hasattr(aiortc.RTCPeerConnection, 'addTransceiver')

    def __str__(self):
        return f"""Supports:
    platform: {self.get_platform()}
    version: {'.'.join(map(str, self.get_version()[:3]))}
    isIOS: {self.is_ios}
    isWebRTCSupported: {self.is_webrtc_supported()}
    isPlatformSupported: {self.is_platform_supported()}
    isUnifiedPlanSupported: {self.is_unified_plan_supported()}"""

supports = Supports()