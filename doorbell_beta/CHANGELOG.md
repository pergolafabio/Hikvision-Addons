# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 3.0.0.beta.7 - 2022-03-06

### Added

- Changed sensor 'off' state to 5 sec instead of 1 for testing
- Added ISAPI alarm
- Added alarm sensor for 'door not open/closed' alarm
- Added Face Access Terminal as supported device

## 3.0.0.beta.1 - 2022-02-23

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
