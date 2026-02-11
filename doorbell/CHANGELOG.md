# Changelog

## 3.0.32 - 2026-02-11

### Fix

- Doorbell name failing when spaces are used
- Improve manual mqtt config for validation errors

## 3.0.30 - 2026-02-10

### Changed/Added

- Updated requirements to offer new functionality!
- New image entity, take snapshot button updates the image entity
- Ring event also creates a snapshot automaticly
- Pressing the call status button manually also updates the call sensor entity
- No more timestamp on the snapshot image, since we are now using the image mqtt entity
- Added a backlight control mode for outdoor stations
- Add control_source_decoded  card_user_id and unlock_type to attributes when door was opened
- Add dev number to logging on incoming ring event, to hopefull identify what button on outdoor station was pressed
- Fix for dev number, when not able to parse
- Improve offline device handling

## 3.0.27 - 2026-01-23

### Changed

- Using a slim image now, makes the App / image 5 x times smaller 1GB => 200MB
- Added:  Extra input commands to align with all MQTT entities (callerInfo/callStatus/takeSnapshot)
- Added:  An extra button (Take Snapshot), this takes a snapshot from the outdoor station and saves the image in the /media drive! (For now :-) ) When you are pressing the button from an indoor station, it will login to the outdoor station first, this works ONLY when the admin credentials are the same, could be usefull for people that only have access to indoor stations
- Fix: gracefully handle invalid ISAPI input strings


## 3.0.26 - 2025-12-15

### Changed

- Added also a call sensor for indoor stations, there is no event for indoor stations, so you need to manually poll it with the call_state_poll config option, usefull when you dont have access to outdoor station (appertment building)

## 3.0.25 - 2025-11-12

### Changed

- Put the call sensor back to idle after 60 sec, some devices dont have the "dismissed" event so sensor stays in "ringing" state
- COM ports on Indoor stations do now have the ability to also CLOSE instead of OPEN only
- Add support for DS-KIT6Q 10509
- Fix polling for scene / alarm mode when configured on multiple Indoor Stations
- Added an optional polling for the call state sensor, for devices running newer firmware 3.7.x, where ringing event is not in the SDK anymore, there is a new app-config "call_state_poll", you can configure it with an integer to poll every xx seconds

## 3.0.24- 2024-10-07

### Fix

- Fix for: uses the deprecated option 'object_id' to set the default entity id.

## 3.0.22 - 2025-05-04

### Changed

- Added date/time in the motion event

## 3.0.21 - 2025-04-01

### Added

- Added support for DS-K1T341CMF and DS-K1T6QT-F72M

## 3.0.19 - 2024-11-19

### Added

- Added support for K1T341BM and K1T673M

## 3.0.18 - 2024-11-05

### Added

- Previously, the ISAPI text entity was disabled by default, since it was used for testing commands, now its enabled by default, since it can be usefull to trigger commands that are not part of the app yet, i added a new document with some examle commands... If you are using the service, the output of the ISAPI command will be shown in the attribute text

## 3.0.16 - 2024-10-01

### Added

- Retry added every 15 sec, when the device is offline, when starting the app
- Added support for deviceK1T670M
- When muting twice by mistake, we used a default of "7" to unmuted, and not the previous "0" setting

## 3.0.15 - 2024-06-04

### Added

- For K1T devices a seperate device trigger was created when a fingerscan is verified, now the employee is an attribute
- Added door id as asstribute for magnetic door event and external force alarm
- Added control_source as attribute for illegal card swipe

## 3.0.14 - 2024-01-22

### Added

- Added support for DS-KV9503-WBE1 handling more events
- For K1T devices a seperate device trigger was created when a face is verified, now the employee is an attribute
- Added Call Status button, usefull to poll the call status for devices not supporting the SDK event

### Changed

- Removed support for DS-K1T343MWX (SDK not compatible)

## 3.0.13 - 2024-01-02

### Added

- Added support for DS-K1T343MWX
- Caller info button is not optional anymore, seems K1T devices dont create an incoming ring event, so users can build a polling autimation with this button
- For K1T devices a seperate device trigger is created when a face is verified, the trigger will show the employee id

## 3.0.12 - 2023-11-13

### Added

- Added support for DS-K1T671MF device

## 3.0.10 - 2023-10-02

### Added

- New Mute/Unmute output sound buttons for indoor and outdoor stations
- Default 0 output relays, if none found instead of stopping app and present warning
- Default 0 com relays, if none found instead of stopping app and present warning

## 3.0.8 - 2023-09-25

### Added

- Make mqtt port configurable for standalone containers

## 3.0.7 - 2023-09-20

### Added

- Now also avaible on Dockerhub for standalone containers! https://hub.docker.com/r/pergolafabio/hikvision-doorbell
- Dynamicly add door relays for indoor stations
- Dynamicly add com ports for indoor stations
- Added support for ACS events
- Added support for DS-K1T341AM device
- Added support for DS-K1T342 device
- Changed logging from INFO to DEBUG for polling alarm/scenes

### Fixed

- Fix for hangup button

## 3.0.2 - 2023-09-01

### Added

- Better logging for caller_info, now you see it as attribute on caller_info button when pressed

## 3.0.1 - 2023-08-30

### Fixed

- Fix for caller_info button

## 3.0.0-beta.34 - 2023-08-30

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

- Possibilty to change port 8000 in the App config for the hikvision devices 

## 3.0.0-beta.25 - 2023-07-25

### Added

- Possibilty to define an external broker in the App config

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
- If the App has trouble connecting to the doorbells, the sensors show up as `unavailable`

### Changed

- Update documentation, add section about **MQTT** broker installation
- The App no longer creates simple `binary_sensor`, but  various entities associated to one or more `device`, each visible in the HA UI
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

The app has been completely __overhauled__, with lots of __new features__ and an __improved codebase__ that will aid future integrations and improvements.

### Added

- Handle __multiple doorbells__
    - Customize the __name__ of each doorbell
    - __Command__ each device separately (open door, reboot, etc...)
- Run the app as a standalone __Docker container__, for Home Assistant installations without _supervisor_. (this feature is considered _experimental_ and still to be appropriately tested. Feedback is welcome!)
    - Load __configuration__ from a JSON/YAML file or from environment variables
- Configurable __system logs__
- Events coming from the doorbells are written to the __console__, for easier debugging and troubleshooting
- Automated __testing__ and __release__ using Github Actions
- New __beta channel__ to test pre-release versions of the app
- Add basic __blueprint__ to showcase how to integrate the sensors inside HA

### Changed

- Change the name of the app to __Hikvision Doorbell__
- Improved __documentation__ for both end users and developers
- Changed the format of __input commands__ to: `<command> <doorbell_name> <optional_argument>`
  - The __name__ of the doorbell must be specified as part of the command
- Changed the sensors created inside HA by this App:
  - The doorbell name is part of the sensor name
  - Sensors are initialized to `off` __on startup__
  - Sensors are __`binary_sensors`__
  - Define __`device_class`__ for each sensor

### Deprecated
- Old __configuration options__
- Remove __`aarch64`__ folder of the deprecated app
