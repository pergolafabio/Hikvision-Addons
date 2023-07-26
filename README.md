# Home Assistant Hikvision Add-ons

<p align="center">
    <a href="https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fpergolafabio%2FHikvision-Addons">
        <img src="https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg" alt="Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.">
    </a>
</p>

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

This repository can be added to an Home Assistant OS installation.
It provides the following add-ons:

## [Hikvision Doorbell](hikvision-doorbell/README.md)

Connect to you Hikvision IP doorbells to receive events (motion detection, incoming call, etc..) and relay back commands (reject call, open doors, etc...).

__Note__: This add-on can also run as a standalone Docker container, for HA installations without the add-on store. For more details see the relevant [documentation](hikvision-doorbell/docs/docker.md).

To quickly get started, click the following button:
[![Open your Home Assistant instance and show the dashboard of a Supervisor add-on.](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=aff2db71_hikvision_sdk&repository_url=https%3A%2F%2Fgithub.com%2Fpergolafabio%2FHikvision-Addons)

## [Use Asterisk as Indoor extension](https://github.com/pergolafabio/Hikvision-Addons/blob/dev/asterisk/asterisk.as.indoor.md)

__NOTE__: This is not an add-on, just an alternate way to setup Asterisk without setting up SIP on the devices!
## Donations
 Like my work? You can always [send me a donation](https://paypal.me/pergolafabio).
