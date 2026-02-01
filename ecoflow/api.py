import hashlib
import hmac
import random
import time
from http.client import HTTPConnection
from urllib.parse import urlencode

import requests
from loguru import logger as log


class EcoflowApi:
    access_key = None
    secret_key = None

    def __init__(self, base_url, access_key, secret_key):
        self.base_url = base_url or 'https://api.ecoflow.com'
        self.access_key = access_key
        self.secret_key = secret_key

        # can be used to debug
        # self.debug_requests_on()

    def debug_requests_on(self):
        '''Switches on logging of the requests module.'''
        HTTPConnection.debuglevel = 1

    def generate_nonce(self):
        return str(random.randrange(100000, 999999))

    def generate_sign(self, params, timestamp, nonce):
        all_params = {
            **params,
            **{
                'accessKey': self.access_key,
                'nonce': nonce,
                'timestamp': timestamp
            }
        }

        self.debug(f"all_params = {all_params}, self.secret_key.encode() = {self.secret_key}")

        return hmac \
            .new(self.secret_key.encode(), urlencode(all_params).encode(), hashlib.sha256) \
            .hexdigest()

    def debug(self, message):
        log.debug(f"Ecoflow API debug: {message}")
        pass

    def error(self, message):
        log.error(f"Ecoflow API error occured: {message}")
        pass

    def url(self, path_and_params):
        return f"{self.base_url}{path_and_params}"

    def request(self, method, url, data=None, **kwargs):
        timestamp = str(int(time.time()) * 1000)
        nonce = self.generate_nonce()

        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'accessKey': self.access_key,
            'nonce': nonce,
            'timestamp': timestamp,
            'sign': self.generate_sign({}, timestamp, nonce)
        }
        response = None
        for _ in range(kwargs.get('retries', 3)):
            try:
                response = requests.request(method, url, headers=headers, json=data)

                self.debug(f"{method} {url} with headers = {headers}, data = {data}, response = {response}")

                if response and response.status_code == 200:
                    return response
            except Exception as e:
                self.error(f"Failed to request {url} with headers = {headers}, data = {data}, error = {e}, "
                           f"start retrying...")

        if response:
            self.error(f"Non-success status code: {response.status_code} while requesting {url}")
            raise Exception(f"Non-success status code: {response.status_code}")
        else:
            self.error(f"Failed to request {url}")
            raise Exception(f"Failed to request {url}")

    def get_device_list(self):
        """
        Query the user's bound device list
        Only returns the device bound to itself, not by share.
        """

        return self.request('get', self.url('/iot-open/sign/device/list'))

    def get_device_quote_all(self, sn):
        """
        Query device's all quota infomation
        """

        return self.request('get', self.url(f"/iot-open/sign/device/quota/all?sn={sn}"))

    def get_mqtt_certification(self):
        """
        MQTT certificate acquisition
        Get the MQTT certification, using it for MQTT communication.
        """

        return self.request('get', self.url('/iot-open/sign/certification'))
