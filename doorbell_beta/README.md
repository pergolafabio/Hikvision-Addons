# Home Assistant Add-on: Hikvision Doorbell (__Beta__)

<p align="center">
   <a href="https://img.shields.io/badge/amd64-yes-green.svg">
      <img alt="Supports amd64 Architecture" src="https://img.shields.io/badge/amd64-yes-green.svg">
   </a>
   <a href="https://img.shields.io/badge/aarch64-yes-green.svg">
      <img alt="Supports aarch64 Architecture" src="https://img.shields.io/badge/aarch64-yes-green.svg">
   </a>
   <a href="https://img.shields.io/badge/i386-yes-green.svg">
      <img alt="Supports i386 Architecture" src="https://img.shields.io/badge/i386-yes-green.svg">
   </a>
</p>

Connect your Hikvision IP door stations to Home Assistant to receive events (like motion detection or incoming calls) and send back commands (like opening a door connected to the door station relay or rejecting a call).

__NOTE__: This is the pre-release version of the addon. Bear in mind that it may have unexpected issues.
You feedback is very welcome! If you have any doubt, would like to report an issue or to simply chime in, please have a look at the [Github Issues page](https://github.com/pergolafabio/Hikvision-Addons/issues) and drop us a note!

## Features
- Capture doorbell events: callstatus/motion detection/door unlocked/tamper alarm/dismissed alarm
- Open doors connected to the doorbell (_useful for older devices where port 80 is blocked and `ISAPI` is not available_)
- Remote actions such as answering/rejecting the call, hanging up, etc (via the `ISAPI` API).
_This can be exploited in HA automation. When for example a Zigbee door sensor signals a door opened, the ringing on the indoor stations and on the Hik-Connect devices is stopped. Se the documentation for more details._
- Reboot the door station

## Getting started

- __NOTE__: To use this _beta_ version, enable __Advanced mode__ in you Home Assistant profile:
   - Click on you user name (in the lower-right corner of Home Assistant UI)
   - Scroll down the profile page and toggle __Advanced Mode__
- Add this repository on your local Home Assistance instance by clicking the following button:
<p align="center">
    <a href="https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fpergolafabio%2FHikvision-Addons">
        <img src="https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg" alt="Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.">
    </a>
</p>

- Confirm the **Manage add-on repositories** dialog by clicking **ADD**.
- **Hikvision Doorbell (Beta)** should be available in the _Add-on store_ of your Home Assistant. (If it is not visible after some minutes, reload the store page by navigating to _Settings_ -> _Add-ons_ -> _Add-on store_).
- Select the **Hikvision Doorbell (Beta)** add-on, then click **INSTALL**.
- Have a look at the **Documentation** tab of the add-on to setup the required configuration and to understand how this addon can be integrated in Home Assistant
(The documentation can also be browsed online in the [Github repo](DOCS.md)).

## Supported devices
This devices has been reported to be working from other HA users.
If your device is not on the list, we are happy to include it. Just [open an issue here][issue] on GitHub and let us know the kind of device you have.

- DS-KV8413
- KD8003
- DS-KV8113
- KV8213
- DS-KV6113

## Additional resources
- [Add-on documentation](DOCS.md)
- [Development documentation](docs/)
- [Home Assistant community forum](https://community.home-assistant.io/t/add-on-hikvision-doorbell-integration/532796)

## Contributing

This is an active open-source project. We are always open to people who want to
use the code or contribute to it. Thank you for being involved! :heart_eyes:

Have a look at the [documentation folder](docs/) for more information.

### Contributors
<a href="https://github.com/pergolafabio/Hikvision-Addons/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=pergolafabio/Hikvision-Addons" />
</a>

Made with [contrib.rocks](https://contrib.rocks).

## Donations
 Like my work? You can always [send me a donation](https://paypal.me/pergolafabio).

## Credits
This add-on was initially inspired by [this script](https://github.com/laszlojakab/hikvision-intercom-python-demo).
