# Home Assistant Add-on: Hikvision Doorbell

## Configuration
**Note**: _Remember to restart the add-on when the configuration is changed._

The following configuration options are available to be setup using the **Configuration** tab of this add-on in the Home Assistant interface:

### Network
Configure the connection to the doorstation. If not provided, the default value are used.

| Name          | Default       | Description                           |
| --------      | ----          | ----                                  |
| ip            | 192.168.0.70  | IP address of your outdoor station
| username      | admin         | Username to access your outdoor station
| password      | password      | Password to access your outdoor station
| ip_indoor     | 192.168.0.80  | The IP address of your indoor station (optional, if available)

### Sensors
Configure the name of the sensors that are created in Home Assistant.

| Name              | Default               | Description                           |
| --------          | ----                  | ----                                  |
| sensor_callstatus | hikvision_callstatus  | Call status event
| sensor_dimiss     | hikvision_dismiss     | Call dismissed event
| sensor_motion     | hikvision_motion      | Motion detection alarm
| sensor_door       | hikvision_door        | Door open event
| sensor_tamper     | hikvision_tamper      | Tamper alarm

### General
The following settings are also available:

```yaml
system:
  log_level: WARNING
```

| Name              | Default               | Description                           |
| --------          | ----                  | ----                                  |
| log_level         | WARNING               | The verbosity of the add-on logs. Available options: _ERROR_ _WARNING_ _INFO_ _DEBUG_


## Integrating with Home Assistant

Create the template sensors in your `configuration.yaml`, following the example below.

The state of each sensor is `on` for 1 second when triggered.

The `sensor_door` exports as attributes the `door ID` that was opened as well the badge/key used.

### Example

````yaml
# configuration.yaml
template:
  - sensor:
      - name: hikvision_door
        state: "off"
      - name: hikvision_callstatus
        state: "off"
      - name: hikvision_motion
        state: "off"
      - name: hikvision_tamper
        state: "off"
      - name: hikvision_dismiss
        state: "off"
````

## Sending commands

To open a door or reboot the doorstation, send a text message to the add-on via `stdin`. The available commands are:

| Command   | Description                                               |
| --------  | ----                                                      |
| unlock1   | Unlock the *first* door, if connected to the doorbell station output relay
| unlock2   | Unlock the *second* door, if connected to the doorbell station output relay
| reboot    | Reboot the doorstation

### Example
In the following code, `a53439b8_hikvision_sdk` is the unique add-on ID, check your local Home Assistant instance to correctly set it up.

For more details see the [official documentation]((https://www.home-assistant.io/integrations/hassio/#service-hassioaddon_stdin)) about the `hassio.addon_stdin` service.

#### Unlock a door
This service call unlocks door 1 connected to the output relay of the doorstation.
````yaml
service: hassio.addon_stdin
data:
  addon: a53439b8_hikvision_sdk
  input: unlock1
````

#### Reboot the device
````yaml
service: hassio.addon_stdin
data:
  addon: a53439b8_hikvision_sdk
  input: reboot
````

### Callsignal API

The `callsignal` API is useful to reject the call.
For example it might come in handy in tandem with a sensor monitoring the status of the front door. When someone presses the ring button on the doorbell, if the door is opened by hand without picking up the call, the below service rejects the call.
All indoor stations including the Hik-Connect devices stop ringing.

Available commands are:
| Command     | Description                                               |
| --------    | ----                                                      |
| reject      | Reject the door, the indoor stations stop ringing
| request     | Unknown
| cancle      | Unknown
| answer      | Unknown
| reject      | Unknown
| bellTimeout | Unknown
| hangUp      | Unknown
| deviceOnCall| Unknown

#### Example

N.B.: `a53439b8_hikvision_sdk` is an example of the add-on name, substitute with your own value.

The `ip_indoor` configuration option is important for this to work.
It has been tested on a `DS-KD8003` outdoor unit with indoor stations.
The callsignal command must be sent to the indoor station.
If you dont have an indoor station, just setup `ip_indoor` with the same IP as the outdoor station, so the callsignal will be send to the outdoor unit.

````yaml
service: hassio.addon_stdin
data:
  addon: a53439b8_hikvision_sdk
  input: reject
````

## Support
If you find a bug or need support [open an issue here][issue] on GitHub.
If required by the devs, please attach a copy of your logs in the issue to help us better diagnose the problem!

### Troubleshooting
Have a look at the **Log** tab of the add-on in the Home Assistant UI.

You can increase the verbosity by changing the `system.log_level` configuration option. For instance:
```yaml
system:
  log_level: DEBUG
```

*N.B.*: When the add-on connects to a doorbell for the first time, it might happen that your doorstation gets stuck, because it is downloading the complete backlog of events. A reboot might be required.

