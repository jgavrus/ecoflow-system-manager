from datetime import datetime, timedelta
import json
import os
import signal
import ssl
import sys
import time
from threading import Timer, Thread
from queue import Queue
from zoneinfo import ZoneInfo

import paho.mqtt.client as mqtt
from loguru import logger as log
from prometheus_client import start_http_server, REGISTRY, Gauge, Counter

from ecoflow.auth import EcoflowApplication
from ecoflow.exceptions import EcoflowMetricException
from ecoflow.metrics import EcoflowMetric

log.remove()
log.add(sys.stdout, level="INFO")

asia_tz = ZoneInfo("Asia/Shanghai")


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class EcoflowMQTT:

    def __init__(self, message_queue, device_sn, username, password, addr, port, client_id, timeout_seconds):
        self.message_queue = message_queue
        self.addr = addr
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id
        self.topic = f"/app/device/property/{device_sn}"
        self.timeout_seconds = timeout_seconds
        self.last_message_time = None
        self.client = None
        self.device_sn = device_sn
        self.connect(first_run=True)

        self.idle_timer = RepeatTimer(10, self.idle_reconnect)
        self.idle_timer.daemon = True
        self.idle_timer.start()
        self.log_dict = {}

    def connect(self, first_run=False):
        if not first_run:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception as e:
                log.exception(e)

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, self.client_id)
        self.client.username_pw_set(self.username, self.password)
        self.client.tls_set(certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED)
        self.client.tls_insecure_set(False)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        log.info(f"Connecting to MQTT Broker {self.addr}:{self.port} using client id {self.client_id}")
        self.client.connect(self.addr, self.port)
        self.client.loop_start()

    def idle_reconnect(self):
        delta_condition = (datetime.now(tz=asia_tz) - self.last_message_time).seconds > self.timeout_seconds
        if self.last_message_time and delta_condition:
            log.error(f"No messages received for {self.timeout_seconds} seconds. Reconnecting to MQTT")
            # We pull the following into a separate process because there are actually quite a few things that can go
            # wrong inside the connection code, including it just timing out and never returning. So this gives us a
            # measure of safety around reconnection
            while True:
                connect_process = Thread(target=self.connect)
                connect_process.start()
                try:
                    connect_process.join(timeout=60)
                    if not connect_process.is_alive():
                        log.info("Reconnection successful, continuing")
                        # Reset last_message_time here to avoid a race condition between idle_reconnect getting called again
                        # before on_connect() or on_message() are called
                        self.last_message_time = None
                        break
                except Exception as e:
                    log.error(f"Reconnection errored out, or timed out, attempted to reconnect... {e}")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        log.info(f"Connected with result code {reason_code}, {userdata}, {flags}")

        # Initialize the time of last message at least once upon connection so that other things that rely on that to be
        # set (like idle_reconnect) work
        self.last_message_time = datetime.now(tz=asia_tz)
        match reason_code:
            case "Success":
                topic = f"/open/{self.username}/{self.device_sn}/quota"
                self.client.subscribe(topic)
                log.info(f"Subscribed to MQTT topic {topic}")

            case "Keep alive timeout":
                log.error("Failed to connect to MQTT: connection timed out")
            case "Unsupported protocol version":
                log.error("Failed to connect to MQTT: unsupported protocol version")
            case "Client identifier not valid":
                log.error("Failed to connect to MQTT: invalid client identifier")
            case "Server unavailable":
                log.error("Failed to connect to MQTT: server unavailable")
            case "Bad user name or password":
                log.error("Failed to connect to MQTT: bad username or password")
            case "Not authorized":
                log.error("Failed to connect to MQTT: not authorised")
            case _:
                log.error(f"Failed to connect to MQTT: another error occured: {reason_code}")

        return client

    @staticmethod
    def on_disconnect(client, userdata, flags, reason_code, properties):
        if reason_code > 0:
            log.error(f"Unexpected MQTT disconnection: {reason_code}. Will auto-reconnect")
            time.sleep(5)

    def on_message(self, client, userdata, message):
        self.message_queue.put(message.payload.decode("utf-8"))
        self.last_message_time = datetime.now(tz=asia_tz)


class Worker:

    def __init__(self, ecoflow_mqtt_client: EcoflowMQTT, ecoflow_application: EcoflowApplication,
                 message_queue, device_name, device_sn, collecting_interval_seconds=5):
        self.ecoflow_mqtt_client = ecoflow_mqtt_client
        self.ecoflow_application = ecoflow_application
        self.message_queue = message_queue
        self.device_name = device_name
        self.device_sn = device_sn
        self.collecting_interval_seconds = collecting_interval_seconds
        self.metrics_collector = {}
        self.online = Gauge("ecoflow_online", "1 if device is online", labelnames=["device"])
        self.mqtt_messages_receive_total = Counter("ecoflow_mqtt_messages_receive_total", "total MQTT messages",
                                                   labelnames=["device"])

    def flatten_dict(self, data: dict, parent_key: str = "", sep: str = ".") -> dict:
        flat = {}

        for key, value in data.items():
            new_key = f"{key}" if parent_key else str(key)

            if isinstance(value, dict):
                flat.update(self.flatten_dict(value, new_key, sep))
            else:
                flat[new_key] = value

        return flat

    def loop(self):
        # time.sleep(self.collecting_interval_seconds)
        while True:
            queue_size = self.message_queue.qsize()
            api_payload = self.ecoflow_application.api.get_device_quote_all(self.device_sn).json()
            if queue_size > 0:
                log.info(f"Processing {queue_size} event(s) from the message queue")
                self.online.labels(device=self.device_name).set(1)
                self.mqtt_messages_receive_total.labels(device=self.device_name).inc(queue_size)
            elif not api_payload and not queue_size:
                log.info("Message queue is empty. Assuming that the device is offline")
                self.online.labels(device=self.device_name).set(0)
                # Clear metrics for NaN (No data) instead of last value
                for metric in self.metrics_collector:
                    metric.clear()

            while self.message_queue.empty() or api_payload.get('data'):
                time.sleep(self.collecting_interval_seconds)
                api_payload = self.ecoflow_application.api.get_device_quote_all(self.device_sn).json()

                if not self.message_queue.empty():
                    queue_payload = self.message_queue.get(timeout=0.1)
                else:
                    queue_payload = {}

                # log.debug(f"Recived payload: {payload}")
                if not api_payload and not queue_payload:
                    log.info('has no api_payload and no queue_payload')
                    continue

                try:
                    if isinstance(queue_payload, str):
                        payload = json.loads(queue_payload)
                    elif isinstance(queue_payload, dict):
                        payload = queue_payload
                    else:
                        payload = {}
                    payload = payload | api_payload.get('data', {})
                    self.process_payload(payload)
                except KeyError as key:
                    log.error(f"Failed to extract key {key} from payload: {queue_payload} or {api_payload}")
                except Exception as error:
                    log.error(f"Failed to parse payload: {queue_payload} or {api_payload} Error: {error}")
                    continue

    def get_metric_by_ecoflow_payload_key(self, ecoflow_payload_key):
        for metric in self.metrics_collector:
            if metric.ecoflow_payload_key == ecoflow_payload_key:
                # log.debug(f"Found metric {metric.name} linked to {ecoflow_payload_key}")
                return metric
        # log.debug(f"Cannot find metric linked to {ecoflow_payload_key}")
        return False

    def process_payload(self, params):
        # log.debug(f"Processing params: {params}")
        parsed_params = self.flatten_dict(params)
        for ecoflow_payload_key, ecoflow_payload_value in parsed_params.items():
            # log.info(f'processing {ecoflow_payload_key}: {ecoflow_payload_value}')
            if ecoflow_payload_key == 'quota_cloud_ts' and isinstance(ecoflow_payload_value, str):
                date = datetime.fromisoformat(ecoflow_payload_value)
                date = date.replace(tzinfo=asia_tz)
                self.ecoflow_mqtt_client.last_message_time = date
                continue
            if not isinstance(ecoflow_payload_value, (int, float)):
                # log.warning(f"Skipping unsupported metric {ecoflow_payload_key}: {ecoflow_payload_value}")
                continue

            metric = self.metrics_collector.get(ecoflow_payload_key)
            if not metric:
                try:
                    metric = EcoflowMetric(ecoflow_payload_key, self.device_name)
                except EcoflowMetricException as error:
                    log.error(error)
                    continue
                log.info(f"Created new metric from payload key {metric.ecoflow_payload_key} -> {metric.name}")
                self.metrics_collector[ecoflow_payload_key] = metric

            metric.set(ecoflow_payload_value)

def signal_handler(signum, frame):
    log.info(f"Received signal {signum}. Exiting...")
    sys.exit(0)


def main():
    # Register the signal handler for SIGTERM
    signal.signal(signal.SIGTERM, signal_handler)

    # Disable Process and Platform collectors
    for coll in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(coll)

    device_sn = os.getenv("DEVICE_SN")
    device_name = os.getenv("DEVICE_NAME")
    ecoflow_access = os.getenv("ACCESS_KEY")
    ecoflow_secret = os.getenv("SECRET_KEY")
    ecoflow_api_host = os.getenv("ECOFLOW_API_HOST", "api.ecoflow.com")
    exporter_port = int(os.getenv("EXPORTER_PORT", "9091"))
    collecting_interval_seconds = int(os.getenv("COLLECTING_INTERVAL", "1"))
    timeout_seconds = int(os.getenv("MQTT_TIMEOUT", "120"))

    if not all([device_sn, ecoflow_access, ecoflow_secret]):
        log.error("Please, provide all required environment variables: DEVICE_SN, ACCESS_KEY, SECRET_KEY")
        sys.exit(1)

    try:
        ecoflow_app = EcoflowApplication(ecoflow_access, ecoflow_secret, ecoflow_api_host)
    except Exception as error:
        log.error(error)
        sys.exit(1)

    message_queue = Queue()

    ecoflow_mqtt_client = EcoflowMQTT(message_queue, device_sn, ecoflow_app.mqtt_username, ecoflow_app.mqtt_password,
                                      ecoflow_app.mqtt_url, ecoflow_app.mqtt_port, ecoflow_app.mqtt_client_id,
                                      timeout_seconds)

    metrics = Worker(ecoflow_mqtt_client, ecoflow_app, message_queue, device_name, device_sn,
                     collecting_interval_seconds)

    start_http_server(exporter_port)

    try:
        metrics.loop()

    except KeyboardInterrupt:
        log.info("Received KeyboardInterrupt. Exiting...")
        sys.exit(0)


if __name__ == '__main__':
    main()
