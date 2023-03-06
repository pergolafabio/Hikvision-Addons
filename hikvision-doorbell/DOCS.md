# Home Assistant Add-on: Hikvision Doorbell

## Configuration
**Note**: _Remember to restart the add-on when the configuration is changed._

The following configuration options are available to be setup using the **Configuration** tab of this add-on in the Home Assistant interface:

### Doorbells
Configure the connection to the doorbells. If a value is not defined, the default setting is used.

For each of your doorbells, repeat the following configuration:

| Option        | Default       | Description                           |
| --------      | ----          | ----                                  |
| name          |               | Custom name for this doorbell (visibile in the HA UI and the sensors names)
| ip            |               | IP address of the doorbell
| username      | admin         | Username to access the doorbell
| password      |               | Password to access the doorbell

#### Example config
The following configuration setups two doorbells, named `Front door` and `Rear door`:
```yaml
- name: "Front door"
  ip: 192.168.0.1
  username: admin
  password: password  

- name: "Rear door"
  ip: 192.168.0.2
  username: admin
  password: password
```

### System
The following system settings are available:

| Name              | Default               | Description                           |
| --------          | ----                  | ----                                  |
| log_level         | WARNING               | The verbosity of the add-on logs. Available options: _ERROR_ _WARNING_ _INFO_ _DEBUG_
| sdk_log_level     | NONE               | The verbosity of the Hikvision SDK logs. Available options: _NONE_ _ERROR_ _INFO_ _DEBUG_
#### Example config
```yaml
log_level: WARNING
sdk_log_level: NONE
```

## Integrating with Home Assistant

There are two ways this add-on can be integrated with Home Assistant:
- MQTT integration (recommended)
- REST integration (legacy)

### MQTT integration

**NOTE**: Requires a running MQTT broker.

You can use the officially supported __Mosquitto broker__, available in the official add-ons section of your Home Assistant instance. 
You can quickly set it up by clicking the following button:
[![Open your Home Assistant instance and show the dashboard of a Supervisor add-on.](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=core_mosquitto), or by manually finding it inside your `Add-on store`.

After you have started the __Mosquitto broker__ add-on, you should be able to automatically connect Home Assistant to the broker by going to `Settings` -> `Devices & Services` -> `MQTT`, and clicking `Configure`.

After you have setup the broker, you can start the __Hikvision Doorbell__ add-on, and each doorbell you have configured should be visible a a device under `Settings` -> `Devices & Services` -> `Devices (tab)`.

### REST integration
__Automatically enabled__ whenever there is no __MQTT broker__ available. 

This integration, while supported, is discouraged for new installations, but still available whenever you are unable to run an MQTT broker.
Due to the limitations of the Home Assistant _REST API_, it cannot provide a complete set of features as does the MQTT integration.
(e.g.: devices and button configurable from the HA UI)

The entities created by this integration are all binary sensors.
When triggered, the state of each binary sensor is `on` for 5 seconds.

The `door` sensors exports as attributes the `door ID` that was opened as well the badge/key used.


## Sending commands to the doorbells
There are two ways in which you can interact with your doorbells, depending on the type of integration you have set up with Home Assistant (see previous chapter).

### MQTT integration
The MQTT integration automatically provides [switches](https://www.home-assistant.io/integrations/switch/) and [buttons](https://www.home-assistant.io/integrations/button/) you can toggle and react to from the Home Assistant UI or from your own automations.
The following entities are available for each of you doorbells, depending wether the unit is an _indoor_ or _outdoor_ one:

- Sensors
  - Call state (idle, ringing, dismissed)
- Switches
  - Door relay (to open the door connected to the output relays of the device)
- Buttons
  - Answer call
  - Reject call
  - Reboot (to reboot the device)

### STDIN service
If you don't have the MQTT integration set up, you can still interact with the devices by sending a text message to the add-on on its `standard input` (STDIN).
You can use the built-in `hassio.addon_stdin` service provided by Home Assistant.

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

#### Example
For more details see the [official documentation]((https://www.home-assistant.io/integrations/hassio/#service-hassioaddon_stdin)) about the `hassio.addon_stdin` service.

#### Unlock a door
This service unlocks the door connected to the _1st_ output relay of the door station named `Front door`:
````yaml
service: hassio.addon_stdin
data:
  addon: aff2db71_hikvision_doorbell
  input: unlock front_door 1
````

#### Reboot the device
To reboot the doorbell named `Rear door`:
````yaml
service: hassio.addon_stdin
data:
  addon: aff2db71_hikvision_doorbell
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
  addon: aff2db71_hikvision_doorbell
  input: reject indoor_unit
````

## Support
If you find a bug or need support [open an issue here](https://github.com/pergolafabio/Hikvision-Addons/issues/new) on GitHub.
If possible, please provide a copy of your logs in the issue form to help us better diagnose the problem!

### Troubleshooting
Have a look at the **Log** tab of the add-on in the Home Assistant UI.

You can increase the verbosity by changing the `system.log_level` configuration option. For instance:
```yaml
system:
  log_level: DEBUG
  sdk_log_level: DEBUG
```

*N.B.*: When the add-on connects to a doorbell for the first time, it might happen that your door station gets stuck, because it is downloading the complete backlog of events. A reboot might be required.

