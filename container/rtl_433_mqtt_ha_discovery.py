import paho.mqtt.client as mqtt
import certifi
import os
import time
import json
import logging
import re


# For additional documentation see basis for this file at:
# https://github.com/merbanan/rtl_433/blob/master/examples/rtl_433_mqtt_hass.py


logger = logging.getLogger(__name__)
log_handler = logging.StreamHandler()
log_formatter = logging.Formatter(
    "%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s"
)
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)
logger.setLevel(logging.INFO)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT: Connected to broker.")
        logger.info(f"MQTT: Subscribe: {RTL_433_MQTT_TOPIC}")
        client.subscribe(RTL_433_MQTT_TOPIC)
    else:
        logger.error(f"MQTT: Failed to connect, rc: {rc}")


def on_message(client, userdata, msg):
    logger.debug(f"MQTT: Message received: f{str(msg.payload.decode('utf-8'))}")
    logger.debug(
        f"MQTT: Message topic: {msg.topic}, qos: {msg.qos}, retain flag: {msg.retain}"
    )

    try:
        data = json.loads(msg.payload.decode("utf-8"))

        topicprefix = "/".join(msg.topic.split("/", 2)[:2])
        topicprefix = "rtl_433"
        bridge_event_to_hass(client, topicprefix, data)

    except json.decoder.JSONDecodeError:
        logger.error("JSON decode error: " + msg.payload.decode("utf-8"))


BOOL_TRUES = ["true", "yes", "1"]

RTL_433_RETAIN = os.getenv("RTL_433_RETAIN", "false").lower() in BOOL_TRUES
RTL_433_FORCE_UPDATE = os.getenv("RTL_433_FORCE_UPDATE", "false").lower() in BOOL_TRUES
RTL_433_MQTT_TOPIC = os.getenv(
    "RTL_433_MQTT_TOPIC",
    "rtl_433/+/events",
)
RTL_433_DEVICE_TOPIC_SUFFIX = os.getenv(
    "RTL_433_DEVICE_TOPIC_SUFFIX",
    "devices[/type][/model][/subtype][/channel][/id]",
)
RTL_433_INTERVAL = int(os.getenv("RTL_433_INTERVAL", 600))
RTL_433_EXPIRE_AFTER = int(os.getenv("RTL_433_EXPIRE_AFTER", 0))
RTL_433_IDS = os.getenv("RTL_433_IDS", "").split(",")

MQTT_BROKER = os.getenv("MQTT_BROKER", default="mqtt")
MQTT_PORT = os.getenv("MQTT_PORT", default=8883)
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", default=f"rtl_433-mqtt-ha-discovery")
MQTT_USERNAME = os.getenv("MQTT_USERNAME", default=None)
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", default=None)

HA_DISCOVERY_PREFIX = os.getenv("HA_DISCOVERY_PREFIX", "homeassistant")


discovery_timeouts = {}

# Fields that get ignored when publishing to Home Assistant
# (reduces noise to help spot missing field mappings)
SKIP_KEYS = [
    "type",
    "model",
    "subtype",
    "channel",
    "id",
    "mic",
    "mod",
    "freq",
    "sequence_num",
    "message_type",
    "exception",
    "raw_msg",
]


# Global mapping of rtl_433 field names to Home Assistant metadata.
# @todo - should probably externalize to a config file
# @todo - Model specific definitions might be needed

mappings = {
    "temperature_C": {
        "device_type": "sensor",
        "object_suffix": "T",
        "config": {
            "device_class": "temperature",
            "name": "Temperature",
            "unit_of_measurement": "°C",
            "value_template": "{{ value|float|round(1) }}",
            "state_class": "measurement",
        },
    },
    "temperature_1_C": {
        "device_type": "sensor",
        "object_suffix": "T1",
        "config": {
            "device_class": "temperature",
            "name": "Temperature 1",
            "unit_of_measurement": "°C",
            "value_template": "{{ value|float|round(1) }}",
            "state_class": "measurement",
        },
    },
    "temperature_2_C": {
        "device_type": "sensor",
        "object_suffix": "T2",
        "config": {
            "device_class": "temperature",
            "name": "Temperature 2",
            "unit_of_measurement": "°C",
            "value_template": "{{ value|float|round(1) }}",
            "state_class": "measurement",
        },
    },
    "temperature_F": {
        "device_type": "sensor",
        "object_suffix": "F",
        "config": {
            "device_class": "temperature",
            "name": "Temperature",
            "unit_of_measurement": "°F",
            "value_template": "{{ value|float|round(1) }}",
            "state_class": "measurement",
        },
    },
    # This diagnostic sensor is useful to see when a device last sent a value,
    # even if the value didn't change.
    # https://community.home-assistant.io/t/send-metrics-to-influxdb-at-regular-intervals/9096
    # https://github.com/home-assistant/frontend/discussions/13687
    "time": {
        "device_type": "sensor",
        "object_suffix": "UTC",
        "config": {
            "device_class": "timestamp",
            "name": "Timestamp",
            "entity_category": "diagnostic",
            "enabled_by_default": False,
            "icon": "mdi:clock-in",
        },
    },
    "battery_ok": {
        "device_type": "sensor",
        "object_suffix": "B",
        "config": {
            "device_class": "battery",
            "name": "Battery",
            "unit_of_measurement": "%",
            "value_template": "{{ float(value) * 99 + 1 }}",
            "state_class": "measurement",
            "entity_category": "diagnostic",
        },
    },
    "humidity": {
        "device_type": "sensor",
        "object_suffix": "H",
        "config": {
            "device_class": "humidity",
            "name": "Humidity",
            "unit_of_measurement": "%",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "humidity_1": {
        "device_type": "sensor",
        "object_suffix": "H1",
        "config": {
            "device_class": "humidity",
            "name": "Humidity 1",
            "unit_of_measurement": "%",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "humidity_2": {
        "device_type": "sensor",
        "object_suffix": "H2",
        "config": {
            "device_class": "humidity",
            "name": "Humidity 2",
            "unit_of_measurement": "%",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "moisture": {
        "device_type": "sensor",
        "object_suffix": "H",
        "config": {
            "device_class": "humidity",
            "name": "Moisture",
            "unit_of_measurement": "%",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "pressure_hPa": {
        "device_type": "sensor",
        "object_suffix": "P",
        "config": {
            "device_class": "pressure",
            "name": "Pressure",
            "unit_of_measurement": "hPa",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "pressure_kPa": {
        "device_type": "sensor",
        "object_suffix": "P",
        "config": {
            "device_class": "pressure",
            "name": "Pressure",
            "unit_of_measurement": "kPa",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "wind_speed_km_h": {
        "device_type": "sensor",
        "object_suffix": "WS",
        "config": {
            "device_class": "wind_speed",
            "name": "Wind Speed",
            "unit_of_measurement": "km/h",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "wind_avg_km_h": {
        "device_type": "sensor",
        "object_suffix": "WS",
        "config": {
            "device_class": "wind_speed",
            "name": "Wind Speed",
            "unit_of_measurement": "km/h",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "wind_avg_mi_h": {
        "device_type": "sensor",
        "object_suffix": "WS",
        "config": {
            "device_class": "wind_speed",
            "name": "Wind Speed",
            "unit_of_measurement": "mi/h",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "wind_avg_m_s": {
        "device_type": "sensor",
        "object_suffix": "WS",
        "config": {
            "device_class": "wind_speed",
            "name": "Wind Average",
            "unit_of_measurement": "km/h",
            "value_template": "{{ (float(value|float) * 3.6) | round(2) }}",
            "state_class": "measurement",
        },
    },
    "wind_speed_m_s": {
        "device_type": "sensor",
        "object_suffix": "WS",
        "config": {
            "device_class": "wind_speed",
            "name": "Wind Speed",
            "unit_of_measurement": "km/h",
            "value_template": "{{ float(value|float) * 3.6 }}",
            "state_class": "measurement",
        },
    },
    "gust_speed_km_h": {
        "device_type": "sensor",
        "object_suffix": "GS",
        "config": {
            "device_class": "wind_speed",
            "name": "Gust Speed",
            "unit_of_measurement": "km/h",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "wind_max_km_h": {
        "device_type": "sensor",
        "object_suffix": "GS",
        "config": {
            "device_class": "wind_speed",
            "name": "Wind max speed",
            "unit_of_measurement": "km/h",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "wind_max_m_s": {
        "device_type": "sensor",
        "object_suffix": "GS",
        "config": {
            "device_class": "wind_speed",
            "name": "Wind max",
            "unit_of_measurement": "km/h",
            "value_template": "{{ (float(value|float) * 3.6) | round(2) }}",
            "state_class": "measurement",
        },
    },
    "gust_speed_m_s": {
        "device_type": "sensor",
        "object_suffix": "GS",
        "config": {
            "device_class": "wind_speed",
            "name": "Gust Speed",
            "unit_of_measurement": "km/h",
            "value_template": "{{ float(value|float) * 3.6 }}",
            "state_class": "measurement",
        },
    },
    "wind_dir_deg": {
        "device_type": "sensor",
        "object_suffix": "WD",
        "config": {
            "name": "Wind Direction",
            "unit_of_measurement": "°",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "rain_mm": {
        "device_type": "sensor",
        "object_suffix": "RT",
        "config": {
            "device_class": "precipitation",
            "name": "Rain Total",
            "unit_of_measurement": "mm",
            "value_template": "{{ value|float|round(2) }}",
            "state_class": "total_increasing",
        },
    },
    "rain_rate_mm_h": {
        "device_type": "sensor",
        "object_suffix": "RR",
        "config": {
            "device_class": "precipitation_intensity",
            "name": "Rain Rate",
            "unit_of_measurement": "mm/h",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "rain_in": {
        "device_type": "sensor",
        "object_suffix": "RT",
        "config": {
            "device_class": "precipitation",
            "name": "Rain Total",
            "unit_of_measurement": "mm",
            "value_template": "{{ (float(value|float) * 25.4) | round(2) }}",
            "state_class": "total_increasing",
        },
    },
    "rain_rate_in_h": {
        "device_type": "sensor",
        "object_suffix": "RR",
        "config": {
            "device_class": "precipitation_intensity",
            "name": "Rain Rate",
            "unit_of_measurement": "mm/h",
            "value_template": "{{ (float(value|float) * 25.4) | round(2) }}",
            "state_class": "measurement",
        },
    },
    "tamper": {
        "device_type": "binary_sensor",
        "object_suffix": "tamper",
        "config": {
            "device_class": "safety",
            "force_update": "true",
            "payload_on": "1",
            "payload_off": "0",
            "entity_category": "diagnostic",
        },
    },
    "alarm": {
        "device_type": "binary_sensor",
        "object_suffix": "alarm",
        "config": {
            "device_class": "safety",
            "force_update": "true",
            "payload_on": "1",
            "payload_off": "0",
            "entity_category": "diagnostic",
        },
    },
    "rssi": {
        "device_type": "sensor",
        "object_suffix": "rssi",
        "config": {
            "device_class": "signal_strength",
            "unit_of_measurement": "dB",
            "value_template": "{{ value|float|round(2) }}",
            "state_class": "measurement",
            "entity_category": "diagnostic",
            "enabled_by_default": False,
        },
    },
    "snr": {
        "device_type": "sensor",
        "object_suffix": "snr",
        "config": {
            "device_class": "signal_strength",
            "unit_of_measurement": "dB",
            "value_template": "{{ value|float|round(2) }}",
            "state_class": "measurement",
            "entity_category": "diagnostic",
            "enabled_by_default": False,
        },
    },
    "noise": {
        "device_type": "sensor",
        "object_suffix": "noise",
        "config": {
            "device_class": "signal_strength",
            "unit_of_measurement": "dB",
            "value_template": "{{ value|float|round(2) }}",
            "state_class": "measurement",
            "entity_category": "diagnostic",
            "enabled_by_default": False,
        },
    },
    "depth_cm": {
        "device_type": "sensor",
        "object_suffix": "D",
        "config": {
            "name": "Depth",
            "unit_of_measurement": "cm",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "power_W": {
        "device_type": "sensor",
        "object_suffix": "watts",
        "config": {
            "device_class": "power",
            "name": "Power",
            "unit_of_measurement": "W",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "energy_kWh": {
        "device_type": "sensor",
        "object_suffix": "kwh",
        "config": {
            "device_class": "power",
            "name": "Energy",
            "unit_of_measurement": "kWh",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "current_A": {
        "device_type": "sensor",
        "object_suffix": "A",
        "config": {
            "device_class": "power",
            "name": "Current",
            "unit_of_measurement": "A",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "voltage_V": {
        "device_type": "sensor",
        "object_suffix": "V",
        "config": {
            "device_class": "power",
            "name": "Voltage",
            "unit_of_measurement": "V",
            "value_template": "{{ value|float }}",
            "state_class": "measurement",
        },
    },
    "light_lux": {
        "device_type": "sensor",
        "object_suffix": "lux",
        "config": {
            "name": "Outside Luminance",
            "unit_of_measurement": "lux",
            "value_template": "{{ value|int }}",
            "state_class": "measurement",
        },
    },
    "lux": {
        "device_type": "sensor",
        "object_suffix": "lux",
        "config": {
            "name": "Outside Luminance",
            "unit_of_measurement": "lux",
            "value_template": "{{ value|int }}",
            "state_class": "measurement",
        },
    },
    "uv": {
        "device_type": "sensor",
        "object_suffix": "uv",
        "config": {
            "name": "UV Index",
            "unit_of_measurement": "UV Index",
            "value_template": "{{ value|int }}",
            "state_class": "measurement",
        },
    },
    "uvi": {
        "device_type": "sensor",
        "object_suffix": "uvi",
        "config": {
            "name": "UV Index",
            "unit_of_measurement": "UV Index",
            "value_template": "{{ value|int }}",
            "state_class": "measurement",
        },
    },
    "storm_dist": {
        "device_type": "sensor",
        "object_suffix": "stdist",
        "config": {
            "name": "Lightning Distance",
            "unit_of_measurement": "mi",
            "value_template": "{{ value|int }}",
            "state_class": "measurement",
        },
    },
    "strike_distance": {
        "device_type": "sensor",
        "object_suffix": "stdist",
        "config": {
            "name": "Lightning Distance",
            "unit_of_measurement": "mi",
            "value_template": "{{ value|int }}",
            "state_class": "measurement",
        },
    },
    "strike_count": {
        "device_type": "sensor",
        "object_suffix": "strcnt",
        "config": {
            "name": "Lightning Strike Count",
            "value_template": "{{ value|int }}",
            "state_class": "total_increasing",
        },
    },
    "consumption_data": {
        "device_type": "sensor",
        "object_suffix": "consumption",
        "config": {
            "name": "SCM Consumption Value",
            "value_template": "{{ value|int }}",
            "state_class": "total_increasing",
        },
    },
    "consumption": {
        "device_type": "sensor",
        "object_suffix": "consumption",
        "config": {
            "name": "SCMplus Consumption Value",
            "value_template": "{{ value|int }}",
            "state_class": "total_increasing",
        },
    },
    "channel": {
        "device_type": "device_automation",
        "object_suffix": "CH",
        "config": {
            "automation_type": "trigger",
            "type": "button_short_release",
            "subtype": "button_1",
        },
    },
    "button": {
        "device_type": "device_automation",
        "object_suffix": "BTN",
        "config": {
            "automation_type": "trigger",
            "type": "button_short_release",
            "subtype": "button_1",
        },
    },
}

# Use secret_knock to trigger device automations for Honeywell ActivLink
# doorbells. We have this outside of mappings as we need to configure two
# different configuration topics.
secret_knock_mappings = [
    {
        "device_type": "device_automation",
        "object_suffix": "Knock",
        "config": {
            "automation_type": "trigger",
            "type": "button_short_release",
            "subtype": "button_1",
            "payload": 0,
        },
    },
    {
        "device_type": "device_automation",
        "object_suffix": "Secret-Knock",
        "config": {
            "automation_type": "trigger",
            "type": "button_triple_press",
            "subtype": "button_1",
            "payload": 1,
        },
    },
]

TOPIC_PARSE_RE = re.compile(
    r"\[(?P<slash>/?)(?P<token>[^\]:]+):?(?P<default>[^\]:]*)\]"
)


def sanitize(text):
    """Sanitize a name for Graphite/MQTT use."""
    return text.replace(" ", "_").replace("/", "_").replace(".", "_").replace("&", "")


def rtl_433_device_info(data, topic_prefix):
    """Return rtl_433 device topic to subscribe to for a data element, based on the
    rtl_433 device topic argument, as well as the device identifier"""

    path_elements = []
    id_elements = []
    last_match_end = 0
    # The default for RTL_433_DEVICE_TOPIC_SUFFIX is the same topic structure
    # as set by default in rtl433 config
    for match in re.finditer(TOPIC_PARSE_RE, RTL_433_DEVICE_TOPIC_SUFFIX):
        path_elements.append(
            RTL_433_DEVICE_TOPIC_SUFFIX[last_match_end : match.start()]
        )
        key = match.group(2)
        if key in data:
            # If we have this key, prepend a slash if needed
            if match.group(1):
                path_elements.append("/")
            element = sanitize(str(data[key]))
            path_elements.append(element)
            id_elements.append(element)
        elif match.group(3):
            path_elements.append(match.group(3))
        last_match_end = match.end()

    path = "".join(list(filter(lambda item: item, path_elements)))
    id = "-".join(id_elements)
    return (f"{topic_prefix}/{path}", id)


def publish_config(client, topic, model, object_id, mapping, key=None):
    """Publish Home Assistant auto discovery data."""
    global discovery_timeouts

    device_type = mapping["device_type"]
    object_suffix = mapping["object_suffix"]
    object_name = "-".join([object_id, object_suffix])

    discovery_topic = "/".join(
        [HA_DISCOVERY_PREFIX, device_type, object_id, object_name, "config"]
    )

    # check timeout
    now = time.time()
    if discovery_topic in discovery_timeouts:
        if discovery_timeouts[discovery_topic] > now:
            logger.debug(f"Discovery timeout in the future for: {discovery_topic}")
            return False

    discovery_timeouts[discovery_topic] = now + RTL_433_INTERVAL

    config = mapping["config"].copy()

    # Device Automation configuration is in a different structure compared to
    # all other mqtt discovery types.
    # https://www.home-assistant.io/integrations/device_trigger.mqtt/
    if device_type == "device_automation":
        config["topic"] = topic
        config["platform"] = "mqtt"
    else:
        readable_name = (
            mapping["config"]["name"] if "name" in mapping["config"] else key
        )
        config["state_topic"] = topic
        config["unique_id"] = object_name
        config["name"] = readable_name

    config["device"] = {
        "identifiers": [object_id],
        "name": object_id,
        "model": model,
        "manufacturer": "rtl_433",
    }

    if RTL_433_FORCE_UPDATE:
        config["force_update"] = "true"

    if RTL_433_EXPIRE_AFTER > 0:
        config["expire_after"] = RTL_433_EXPIRE_AFTER

    logger.debug(f"{discovery_topic} : {json.dumps(config)}")

    (result, mid) = client.publish(
        discovery_topic, json.dumps(config), retain=RTL_433_RETAIN
    )
    if result != 0:
        logger.error(
            f"MQTT: Error publishing discovery, result: {result}, topic: {discovery_topic}"
        )
        return False

    return True


def bridge_event_to_hass(client, topic_prefix, data):
    """Translate some rtl_433 sensor data to Home Assistant auto discovery."""

    if "model" not in data:
        logger.debug("Model is not defined. Not publishing HA discovery messages.")
        return

    model = sanitize(data["model"])

    skipped_keys = []
    published_keys = []

    base_topic, device_id = rtl_433_device_info(data, topic_prefix)
    if not device_id:
        # no unique device identifier
        logger.warning(f"No suitable identifier found for model: {model}")
        return

    data_id = str(data.get("id", None))

    if len(RTL_433_IDS) > 0 and data_id not in RTL_433_IDS:
        logger.debug(f"Device ({data_id}) is not in the desired list of device ids.")
        return

    # detect known attributes
    for key in data.keys():
        if key in mappings:
            topic = "/".join([base_topic, key])
            if publish_config(client, topic, model, device_id, mappings[key], key):
                published_keys.append(key)
        else:
            if key not in SKIP_KEYS:
                skipped_keys.append(key)

    if "secret_knock" in data.keys():
        for m in secret_knock_mappings:
            topic = "/".join([base_topic, "secret_knock"])
            if publish_config(client, topic, model, device_id, m, "secret_knock"):
                published_keys.append("secret_knock")

    if published_keys:
        logger.info(f"Published {device_id}: {published_keys}")

        if skipped_keys:
            logger.info(f"Skipped {device_id}: {skipped_keys}")


def run():
    if MQTT_BROKER is None:
        raise Exception("MQTT_BROKER must be defined.")

    client = mqtt.Client(MQTT_CLIENT_ID)

    if MQTT_USERNAME is not None and MQTT_PASSWORD is not None:
        logger.info(f"MQTT: Authentication enabled, connect as: {MQTT_USERNAME}")
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message

    if MQTT_PORT == 8883:
        logger.info("MQTT: Enable TLS.")
        client.tls_set(certifi.where())

    logger.info(f"MQTT: Connect to {MQTT_BROKER}:{MQTT_PORT} ({MQTT_CLIENT_ID})")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    if len(RTL_433_IDS) > 0:
        logger.info(f"Only discovering devices with ids: {RTL_433_IDS}")
    else:
        logger.info("Discovering all devices.")

    logger.info(f"RTL_433_RETAIN: {RTL_433_RETAIN}")

    client.loop_forever()


if __name__ == "__main__":
    run()
