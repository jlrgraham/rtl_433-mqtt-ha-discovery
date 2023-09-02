# rtl_433-to-mqtt

Respond to `rtl_433` data published to an MQTT broker and create the corresponding [Home Assistant](https://www.home-assistant.io/) via [MQTT Discovery](https://www.home-assistant.io/docs/mqtt/discovery/) entries.

Based on:

* [https://github.com/merbanan/rtl_433/blob/master/examples/rtl_433_mqtt_hass.py](https://github.com/merbanan/rtl_433/blob/master/examples/rtl_433_mqtt_hass.py)
* [https://github.com/zacs/rtl_433_ha_autodiscovery/tree/main](https://github.com/zacs/rtl_433_ha_autodiscovery/tree/main)

## Usage

### Kubernetes StatefulSet

    ---
    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
      name: rtl_433-mqtt-ha-discovery
    spec:
      selector:
        matchLabels:
          app: rtl_433-mqtt-ha-discovery
      replicas: 1
      template:
        metadata:
          labels:
            app: rtl_433-mqtt-ha-discovery
        spec:
          terminationGracePeriodSeconds: 0
          containers:
            - env:
                - name: MQTT_BROKER
                  value: mqtt.broker.name.com
                - name: MQTT_USERNAME
                  value: mqtt_user
                - name: MQTT_PASSWORD
                  value: itsasecret
                - name: HA_DISCOVERY_PREFIX
                  value: ha-discovery
              image: jlrgraham/rtl_433-mqtt-ha-discovery:latest
              imagePullPolicy: Always
              name: rtl_433-mqtt-ha-discovery
          restartPolicy: Always

## Settings

All settings are taken from environmental variables at runtime.

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `MQTT_BROKER` | The hostname or IP of the MQTT broker. | `mqtt` |
| `MQTT_PORT` | The connection port on the MQTT broker.  If set to 8883 TLS is automatically used. | 8883 |
| `MQTT_CLIENT_ID` | The client name given to the MQTT broker.  See MQTT Connections for more details. | `rtl_433-mqtt-ha-discovery ` |
| `MQTT_USERNAME` | The username for the MQTT broker. | `None` |
| `MQTT_PASSWORD` | The password for the MQTT broker. | `None` |
| `HA_DISCOVERY_PREFIX` | The configured Home Assistant discovery prefix. | `homeassistant` |
| `RTL_433_MQTT_TOPIC` | The prefix under which `rtl_433` publish data. | `rtl_433/+/events` |
| `RTL_433_DEVICE_TOPIC_SUFFIX` | The MQTT pattern `rtl_433` publishes to. | `devices[/type][/model][/subtype][/channel][/id]` |
| `RTL_433_INTERVAL` | The publish interval in seconds. | 600 |
| `RTL_433_EXPIRE_AFTER` | Set the `expire_after` field on published devices. | 0 |
| `RTL_433_RETAIN` | Controls if published messages are retained. | False |
| `RTL_433_FORCE_UPDATE` | Append `force_update = true` to all configs. | False |
| `RTL_433_IDS` | A comma seperated string of device IDs to publish for.  Empty for all. | `None` |


### MQTT Connections

#### Authentication

Authentication will be attempted only if both `MQTT_USERNAME` and `MQTT_PASSWORD` are supplied.

#### Client ID

The MQTT client ID can be configured with the `MQTT_CLIENT_ID` variable.  This should generally be fixed for a given deployment.

#### TLS

If the MQTT broker port configuration is set to 8883 then the connector will automatically attempt to enable TLS for the connection to the broker.  The standard [Python certifi package](https://pypi.org/project/certifi/) will be used for CA roots, so public certs (ie: Let's Encrypt + others) should just work.

### MQTT Topics

There are two primary topic configuration controls: `RTL_433_MQTT_TOPIC ` and `HA_DISCOVERY_PREFIX`.

The `RTL_433_MQTT_TOPIC ` setting will control the subscription in MQTT used for `rtl_433` data.

The `HA_DISCOVERY_PREFIX` setting should match [discovery prefix setting](https://www.home-assistant.io/docs/mqtt/discovery/#discovery_prefix) in Home Assistant.

## DockerHub Image

This script is available in a Docker image from: [https://hub.docker.com/repository/docker/jlrgraham/rtl_433-mqtt-ha-discovery/](https://hub.docker.com/repository/docker/jlrgraham/rtl_433-mqtt-ha-discovery/)
