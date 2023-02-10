Like my work? You can always send me a donation: https://paypal.me/pergolafabio

# Home Assistant Add-on: Hikvision SDK for Door Intercoms

## What can it do? 
- It listen for events: callstatus/motion detection/door unlocked/tamper alarm/dimissed alarm
- It can open a door, usefull for older devices where ISAPI is not possible, when port 80 is blocked
- It can reboot your doorstation
- It can send a callsignal command, like answer/reject,hangup ... verry usefull if you have for example a zigbee door sensor, if you open the door by hand, you can drop the ring signal on the indoor stations/or stop hikconnect devices ringing :-)

## Get started

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fpergolafabio%2FHikvision-Addons)

PS: On first start of the Addon, its possible that your doorstation gets stuck, sometimes a reboot is needed, because this Add-on will download the complete backlog... its only the first time

## Gonfiguration of the Add-On

````
    "ip": "192.168.0.70" # The IP of your outdoor station
    "ip_indoor": "192.168.0.71", # In case you have an indoor Panel, usefull for the callsignal command, more info below
    "username": "admin", # The username of your outdoor station
    "password": "password" # The password of your outdoor station
    "sensor_door" : "hikvision_door",
    "sensor_callstatus" : "hikvision_callstatus"
    "sensor_motion" : "hikvision_motion"
    "sensor_tamper" : "hikvision_tamper"
    "sensor_dimiss" : "hikvision_dismiss"		
````	

First of all, create the template sensors in your yaml configuration, like below:
When door is opened by key/badge, or when the doorbell is ringing, or motion detected, or tamper alarm, dismiss... the state of the sensors below are "on" for 1 second. The door sensor will have some attributes also, you will see the door ID that was opened, as well the badge/key

## Sensors 

````
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

## Open a door  or reboot the doorstation

To open a door or reboot the doorstation, we need to send a stdin message to the add-on, it can be used with this service below, use as input: unlock1 OR unlock2, depending if you have 2 output relays on your doorstation.

In below example, a53439b8_hikvision_sdk is the addon name, its possible that its different for you

PS: Use underscore! Dont copy/paste from the addon name itself, there its "-" instead of "_"!

````
service: hassio.addon_stdin
data:
  addon: a53439b8_hikvision_sdk
  input: unlock1
````

````
service: hassio.addon_stdin
data:
  addon: a53439b8_hikvision_sdk
  input: reboot
````

## Callsignal

The callsignal service is usefull to reject the call, i personally use it with a zigbee sensor at my door... When someone pressed the doorbutton, if i open the door by hand without pickup up, the below service rejects the call, and all indoor stations stop ringing, including the hikconnect devices.
Available commands are: "request, cancle, answer, reject, bellTimeout, hangUp, deviceOnCall" ... no idea what they do, i only use "reject".

Again, "a53439b8_hikvision_sdk" is an example of the add-on name, it can be different for you...

The "ip_indoor" in the configuration above is important, i have a DS-KD8003 device, with indoor stations, so i need to send the callsignal command to my indoor station... If you dont have an indoor station, just setup the "ip_indoor" with the same IP as the outdoor station, so the callsignal will be send to the outdoor unit.

````
service: hassio.addon_stdin
data:
  addon: a53439b8_hikvision_sdk
  input: reject
````

Creds:
The add-on is based on this script : https://github.com/laszlojakab/hikvision-intercom-python-demo
