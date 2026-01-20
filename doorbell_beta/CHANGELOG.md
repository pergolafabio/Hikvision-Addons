# Changelog

## 3.0.0-beta.97 - 2026-01-20

### Test

- use 3.10.8-slim image

## 3.0.0-beta.96 - 2026-01-16

### Test

- remove outdoor_ip trying another way to capture a screenshot from indoor panel

## 3.0.0-beta.95 - 2026-01-14

### Test

- added outdoor_ip as optional to the addon confog to configure on indoor stations ONLY, as a test to make a snapshot from outdoor stations

## 3.0.0-beta.94 - 2026-01-14

### Test

- Add snapshot from outdoor to hardcoded IP address : 192.168.10.100

## 3.0.0-beta.87 - 2025-12-10

### Change

- Added an optional poll sensor for callstate, for devices running newer firmware 3.7.x, where ringing event is not in the SDK anymore

## 3.0.0-beta.85 - 2025-12-10

### Fix

- fix unique loops for scene / alarm mode

## 3.0.0-beta.80 - 2025-12-04

### Test

- Added close button for com ports on indoor

## 3.0.0-beta.78 - 2025-11-25

### Test

- Put the call sensor back to idle after 60 sec in any case

## 3.0.0-beta.76 - 2024-10-20

### Change

- Add support for DS-KIT6Q 10509

## 3.0.0-beta.75 - 2024-10-07

### Change

- Fix for: uses the deprecated option 'object_id' to set the default entity id.

## 3.0.0-beta.73 - 2024-04-01

### Test

- Test For  DS-K1T341CMF

## 3.0.0-beta.72 - 2024-05-03

### Test

- Test For  DS-K1T6QT-F72M

## 3.0.0-beta.71 - 2024-11-12

### Test

- Test For DS-K1T673M

## 3.0.0-beta.70 - 2024-11-07

### Test

- Test For Ezviz HP7 device

## 3.0.0-beta.69 - 2024-10-07

### Fix

- Fix for mute button, current volume

## 3.0.0-beta.68 - 2024-10-1

### Fix

- Retry added every 15 sec, when the device is offline, when starting the addon

## 3.0.0-beta.66 - 2024-09-10

### Add

- Test for : K1T670M

## 3.0.0-beta.64 - 2024-07-31

### Fix

- When muting twice by mistake, we used a default of "7" to unmuted, and not the previous "0" setting

## 3.0.0-beta.63 - 2024-06-03

### Added

- Employee ID for event: MINOR_FINGERPRINT_COMPARE_PASS

## 3.0.0-beta.62 - 2024-05-05

### Added

- Testing fIsapi alarm for invalid keypad entry

## 3.0.0-beta.61 - 2024-05-05

### Added

- Testing for NVR

## 3.0.0-beta.60 - 2024-04-11

### Added

- Added door id as asstribute for magnetic door event and external force alarm

## 3.0.0-beta.59 - 2024-02-15

### Added

- Added control source as attribute for illegal card swipe

## 3.0.0-beta.57 - 2024-01-22

### Added

- Added support for DS-KV9503-WBE1 handling more events
- For K1T devices a seperate device trigger was created when a face is verified, now the employee is an attribute
- Added Call Status button, usefull to poll the call status for devices not supporting the SDK event

## 3.0.0-beta.53 - 2024-01-08

### Added

- Employee ID is now an attribute payload, instead of making seperate topics

## 3.0.0-beta.52 - 2024-01-06

### Added

- Added support for DS-K1T502DBFWX-C

## 3.0.0-beta.47 - 2023-12-28

### Added

- Added support for DS-K1T343MWX

## 3.0.0-beta.46 - 2023-10-10

### Added

- Added alternative way for callsignal command if ISAPI fails with error 23

## 3.0.0-beta.44 - 2023-09-20

### Added

- Add support for DS-K1T342

## 3.0.0-beta.43 - 2023-09-12

### Added

- Trying to get locks for device DS-K1T341XX
- Dynamicly add door relays for indoor stations
- Dynamicly add com ports for indoor stations 

## 3.0.0-beta.39 - 2023-09-10

### Test

- Some testing to get correct info for locks for device DS-K1T341XX

## 3.0.0-beta.36 - 2023-09-08

### Fixed

- Fixed the hangUp command

## 3.0.0-beta.36 - 2023-09-07

### Added

- Added support for ACS events

## 3.0.0-beta.35 - 2023-09-06

### Added

- Added support for DS-K1T341AM (test)
- Changed logging from INFO to DEBUG for polling alarm/scenes

## 3.0.0-beta.34 - 2023-08-30

## IMPORTANT

- BETA period is over, i have now created a stable release, so you can now copy the config, uninstall the beta addon, install the main release and paste the config...... This main release is the same as the current beta build

### Added

- Added the 2 com ports for indoor station as a switch, have fun with it :-)
- Optional: When you have a Secure Door Control Module(DS-K2M061), door needs to be unlocked from indoor panel, when you configyre "output_relays: 1" in the indoor config, it will create an extra switch for it

## 3.0.0-beta.32 - 2023-08-22

### Changed

- When caller_info is enabled in the config, it will now create an extra button, people with multiple buttons on outdoor, you can now build an automation to retrieve the caller_info on indoor station on incoming "ringing" event, so you know what indoor device is ringing...

## 3.0.0-beta.31 - 2023-08-09

### Added

- Added 2 extra sensors to poll scene and alarm, when you have enabled scenes support on your indoor device (for testing)

## 3.0.0-beta.30 - 2023-08-07

### Added

- Added 2 extra buttons for arm/disarm indoor panels, this can be enabled with "scenes: true" in the config

## 3.0.0-beta.29 - 2023-08-05

### Fixed

- Make sure control_source is updated before changing the door sensor

## 3.0.0-beta.28 - 2023-08-03

### Added

- Optional scenes support for indoor devices, there is a new config option to enable it, so you enable scenes like: “atHome”, “goOut”, “goToBed”, “custom”
- Optional callerinfo for outdoor devices, usefull for intercoms with multiple buttons, the callsensor does now have an new attribute, there is a new config option to enable it

### Change

- if you use "control source" in yor automations, make sure to rename it now to "control_source"

## 3.0.0-beta.27 - 2023-07-28

### Fixed

- Fix for zone as device triggers, they are all visible now

## 3.0.0-beta.26 - 2023-07-26

### Added

- Possibilty to change port 8000 in the add-on config for the hikvision devices 

## 3.0.0-beta.25 - 2023-07-25

### Added

- Possibilty to define an external broker in the add-on config

## 3.0.0-beta.24 - 2022-06-29

### Change

- Revert Device trigger automation for door open events
- Set attribute control source first (key/badge numer), before turning on door relay switch (test)

## 3.0.0-beta.23 - 2022-06-28

### Added

- Device trigger automation for door open events, to capture the control source (swipe/key number)

## 3.0.0-beta.22 - 2022-06-28

### Fixed

- Fix for Zone Alarm Inputs, its now possible to see device triggers for Alarms like Gas, Water, Panic...

## 3.0.0-beta.21 - 2022-06-19

### Fixed

- Fix for 8102 owners, where the output relay doesnt trigger on intercom event

## 3.0.0-beta.20 - 2022-06-23

### Added

- Added support for DS-K1T501SF

## 3.0.0-beta.19 - 2022-04-15

### Added

- Added hangup button
- Changed unlock record attribute for switch relay to "00" when it was empty when using Isapi/... for open door

## 3.0.0-beta.18 - 2022-04-11

### Added

- Added support for DS-HD series?

## 3.0.0-beta.17 - 2022-03-21

### Added

- Testing Alarm input for zones/types
- Changed login method to offline event uploading, preventing backlog om some devices?

## 3.0.0-beta.16 - 2022-03-18

### Added

- Zone alarm device trigger for indoor and outdoor

## 3.0.0-beta.13 - 2022-03-11

### Changed

- Revert `amd64` SDK update

## 3.0.0-beta.10 - 2022-03-11

### Added

- MQTT integration. 
  **Note: requires a running MQTT broker**
- Each doorbell is now visible as a device inside Home Assistant
- New sensors and entities:
  - `Call state` sensor: displays the state of the call (idle, ringing, dismissed)
  - `Buttons` for _accepting_/_rejecting_ the call, _rebooting_ the device
  - `Switches` for controlling the output switches connected to the doorbell unit (to open gates, doors)
  - `Device triggers` for receiving alarm events (motion detection, door not closed, tamper alarm, etc..)
  - Diagnostic `text` entity for testing out ISAPI commands (advanced)
- New configuration option: `output_relays` (to manually specify the number of relays)
- If the add-on has trouble connecting to the doorbells, the sensors show up as `unavailable`

### Changed

- Update documentation, add section about **MQTT** broker installation
- The add-on no longer creates simple `binary_sensor`, but  various entities associated to one or more `device`, each visible in the HA UI
- Update development documentation with overview on software architecture, add `docker-compose.yml` example.
- Update `amd64` SDK to version `6.1.9.4_build20220412`

### Deprecated

- The Home Assistant `REST API` integration is no longer recommended in favor of the `MQTT integration`, and no new features will be added to it

### Fixed

- Sensors no longer disappear on HA restart

## 3.0.0-beta.9 - 2022-03-06

## Fixed

- Quickfix for ISAPI alarm #af214751244b732402375adc6401a1fdd230d15d

## 3.0.0-beta.8 - 2022-03-06

### Changed

- The `door` sensors attribute `Unlock` is a more readable string

### Fixed

- Multiple doorbells no longer conflict with their sensor names #18

## 3.0.0-beta.7 - 2022-03-06

### Added

- Changed sensor 'off' state to 5 sec instead of 1 for testing
- Added ISAPI alarm
- Added alarm sensor for 'door not open/closed' alarm
- Added Face Access Terminal as supported device

## 3.0.0-beta.1 - 2022-02-23

This is the first of the releases made available under the __Beta channel__. Expect some small issues while we iron out the last bugs and get ready for an exiting official release!
You feedback is very welcome! If you have any doubt, would like to report a bug or to simply chime in, please have a look at the [Github Issues page](https://github.com/pergolafabio/Hikvision-Addons/issues) and drop us a note!
Now let's move on to __what's new__:

The addon has been completely __overhauled__, with lots of __new features__ and an __improved codebase__ that will aid future integrations and improvements.

### Added

- Handle __multiple doorbells__
    - Customize the __name__ of each doorbell
    - __Command__ each device separately (open door, reboot, etc...)
- Run the addon as a standalone __Docker container__, for Home Assistant installations without _supervisor_. (this feature is considered _experimental_ and still to be appropriately tested. Feedback is welcome!)
    - Load __configuration__ from a JSON/YAML file or from environment variables
- Configurable __system logs__
- Events coming from the doorbells are written to the __console__, for easier debugging and troubleshooting
- Automated __testing__ and __release__ using Github Actions
- New __beta channel__ to test pre-release versions of the addon
- Add basic __blueprint__ to showcase how to integrate the sensors inside HA

### Changed

- Change the name of the addon to __Hikvision Doorbell__
- Improved __documentation__ for both end users and developers
- Changed the format of __input commands__ to: `<command> <doorbell_name> <optional_argument>`
  - The __name__ of the doorbell must be specified as part of the command
- Changed the sensors created inside HA by this add-on:
  - The doorbell name is part of the sensor name
  - Sensors are initialized to `off` __on startup__
  - Sensors are __`binary_sensors`__
  - Define __`device_class`__ for each sensor

### Deprecated
- Old __configuration options__
- Remove __`aarch64`__ folder of the deprecated addon
