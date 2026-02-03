import json

from loguru import logger as log

from devices.ecoflow.api import EcoflowApi


class EcoflowApplication:
    def __init__(self, ecoflow_access, ecoflow_secret, ecoflow_api_host):
        self.ecoflow_access = ecoflow_access
        self.ecoflow_secret = ecoflow_secret
        self.ecoflow_api_host = ecoflow_api_host
        self.mqtt_url = "mqtt.ecoflow.com"
        self.mqtt_port = 8883
        self.mqtt_username = None
        self.mqtt_password = None
        self.mqtt_client_id = None
        self.api = EcoflowApi(f"https://{self.ecoflow_api_host}", self.ecoflow_access, self.ecoflow_secret)
        self.authorize_with_api()

    def authorize_with_api(self):
        log.info(f"Requesting IoT MQTT credentials")
        request = self.api.get_mqtt_certification()
        response = self.get_json_response(request)

        try:
            self.mqtt_url = response["data"]["url"]
            self.mqtt_port = int(response["data"]["port"])
            self.mqtt_username = response["data"]["certificateAccount"]
            self.mqtt_password = response["data"]["certificatePassword"]
            self.mqtt_client_id = response["data"]["certificateAccount"]
        except KeyError as key:
            raise Exception(f"Failed to extract key {key} from {response}")

        log.info(f"Successfully extracted account: {self.mqtt_username}")

    @staticmethod
    def get_json_response(request):
        if request.status_code != 200:
            raise Exception(f"Got HTTP status code {request.status_code}: {request.text}")
        response = None
        try:
            response = json.loads(request.text)
            response_message = response["message"]
        except KeyError as key:
            raise Exception(f"Failed to extract key {key} from {response}")
        except Exception as error:
            raise Exception(f"Failed to parse response: {request.text} Error: {error}")

        if response_message.lower() != "success":
            raise Exception(f"{response_message}")

        return response
