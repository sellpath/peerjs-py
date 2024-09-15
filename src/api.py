import json
import random
import time
from urllib.parse import urlencode
import requests
from src.util import util
from src.logger import logger
from src.option_interfaces import PeerJSOption

version = "0.1.0"

class API:
    def __init__(self, options: PeerJSOption):
        self._options = options

    def _build_request(self, method: str) -> requests.Response:
        protocol = "https" if self._options.secure else "http"
        host, port, path, key = self._options.host, self._options.port, self._options.path, self._options.key
        url = f"{protocol}://{host}:{port}{path}{key}/{method}"
        params = {
            "ts": f"{int(time.time() * 1000)}{random.random()}",
            "version": version
        }
        url_with_params = f"{url}?{urlencode(params)}"
        return requests.get(url_with_params, headers={"Referrer-Policy": self._options.referrer_policy})

    def retrieve_id(self) -> str:
        try:
            response = self._build_request("id")
            if response.status_code != 200:
                raise Exception(f"Error. Status:{response.status_code}")
            return response.text
        except Exception as error:
            logger.error("Error retrieving ID", error)
            path_error = ""
            if self._options.path == "/" and self._options.host != util.CLOUD_HOST:
                path_error = (" If you passed in a `path` to your self-hosted PeerServer, "
                              "you'll also need to pass in that same path when creating a new "
                              "Peer.")
            raise Exception("Could not get an ID from the server." + path_error)

    def list_all_peers(self) -> list:
        try:
            response = self._build_request("peers")
            if response.status_code != 200:
                if response.status_code == 401:
                    helpful_error = ""
                    if self._options.host == util.CLOUD_HOST:
                        helpful_error = ("It looks like you're using the cloud server. You can email "
                                         "team@peerjs.com to enable peer listing for your API key.")
                    else:
                        helpful_error = ("You need to enable `allow_discovery` on your self-hosted "
                                         "PeerServer to use this feature.")
                    raise Exception("It doesn't look like you have permission to list peers IDs. " + helpful_error)
                raise Exception(f"Error. Status:{response.status_code}")
            return response.json()
        except Exception as error:
            logger.error("Error retrieving list peers", error)
            raise Exception("Could not get list peers from the server." + str(error))