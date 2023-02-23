# Home Assistant Add-on: Hikvision Doorbell

## Configuration
**Note**: _Remember to restart the add-on when the configuration is changed._

The following configuration options are available to be setup using the **Configuration** tab of this add-on in the Home Assistant interface:

### Doorbells
Configure the connection to the doorbells. If not provided, the default values are used.
Repeat the following configuration option for each doorbell:

| Option        | Default       | Description                           |
| --------      | ----          | ----                                  |
| name          |               | Custom name for this doorbell
| ip            |               | IP address of the doorbell
| username      | admin         | Username to access the doorbell
| password      |               | Password to access the doorbell

#### Example config

```yaml
doorbells: 
  - name: "Front door"
    ip: 192.168.0.1
    username: admin
    password: password  
  - name: "Rear door"
    ip: 192.168.0.2
    username: admin
    password: password
```

### General
The following settings are also available:

| Name              | Default               | Description                           |
| --------          | ----                  | ----                                  |
| log_level         | WARNING               | The verbosity of the add-on logs. Available options: _ERROR_ _WARNING_ _INFO_ _DEBUG_
| sdk_log_level     | NONE               | The verbosity of the Hikvision SDK logs. Available options: _NONE_ _ERROR_ _INFO_ _DEBUG_
#### Example config
```yaml
system:
  log_level: WARNING
  sdk_log_level: NONE
```

## Integrating with Home Assistant

This add-on creates multiple sensors inside Home Assistant, each prefixed with the name of the doorbell it is part of.
For instance a doorbell named `Front door` creates the sensor having ID `binary_sensor.front_door_callstatus`.

A basic blueprint showing how to integrate the sensors in you automation is provided as part of this add-on.
The automation displays a notification inside the Home Assistant UI.
To import the blueprint in you Home Assistant installation, click the button:
[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fpergolafabio%2FHikvision-Addons%2Fblob%2Fdev%2Fblueprints%2Fdoorbell-ringing.yaml)

<!-- ### Advanced configuration
Create the template sensors in your `configuration.yaml`, following the example below.

When triggered, the state of each sensor is `on` for 1 second.

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
```` -->

## Sending commands

To open a door or reboot the door station, send a text message to the add-on via its `standard input`. You can use the built-in `hassio.addon_stdin` service provided by Home Assistant.

The input string must be in the format
```
<command> <doorbell_name> <optional_parameter>
```
- `<command>` is one of:

  | Command     | Description                                               |
  | --------    | ----                                                      |
  | unlock      | Unlock the specified door (`<optional_parameter>` must be `1` or `2`) connected to the doorbell station output relay
  | reboot      | Reboot the specified  door station
  | reject      | Reject the incoming call and stop the indoor stations from ringing
  | request     | Unknown
  | cancel      | Unknown
  | answer      | Unknown
  | reject      | Unknown
  | bellTimeout | Unknown
  | hangUp      | Unknown
  | deviceOnCall| Unknown
- `<doorbell_name>` is the custom name given to the doorbell in the configuration options, all lowercase and with whitespace substituted by underscores `_`. 

  E.G.: If the doorbell is named `Front door`, the input string must reference it as `front_door`.

- `<optional_parameter>` can be an additional string, used for instance to specify additional options for a command

### Example
__Note__: In the following examples, `a53439b8_hikvision_doorbell` is the unique add-on ID, check your local Home Assistant instance and substitute it with your own local ID.

For more details see the [official documentation]((https://www.home-assistant.io/integrations/hassio/#service-hassioaddon_stdin)) about the `hassio.addon_stdin` service.

#### Unlock a door
This service unlocks the door connected to the _1st_ output relay of the door station named `Front door`:
````yaml
service: hassio.addon_stdin
data:
  addon: a53439b8_hikvision_doorbell
  input: unlock front_door 1
````

#### Reboot the device
To reboot the doorbell named `Rear door`:
````yaml
service: hassio.addon_stdin
data:
  addon: a53439b8_hikvision_doorbell
  input: reboot rear_door
````

#### Reject a call
It might come in handy in tandem with a sensor monitoring the status of the front door. When someone presses the ring button on the doorbell, if the door is opened by hand without picking up the call, the below service rejects the call.
All indoor stations including the Hik-Connect devices stop ringing.

This example has been tested on a `DS-KD8003` outdoor unit with indoor stations named `Indoor unit`.
This type of command must be sent to an indoor station only.

````yaml
service: hassio.addon_stdin
data:
  addon: a53439b8_hikvision_doorbell
  input: reject indoor_unit
````

## Support
If you find a bug or need support [open an issue here](https://github.com/pergolafabio/Hikvision-Addons/issues/new) on GitHub.
If required by the developers, please attach a copy of your logs in the issue to help us better diagnose the problem!

### Troubleshooting
Have a look at the **Log** tab of the add-on in the Home Assistant UI.

You can increase the verbosity by changing the `system.log_level` configuration option. For instance:
```yaml
system:
  log_level: DEBUG
  sdk_log_level: DEBUG
```

*N.B.*: When the add-on connects to a doorbell for the first time, it might happen that your door station gets stuck, because it is downloading the complete backlog of events. A reboot might be required.

