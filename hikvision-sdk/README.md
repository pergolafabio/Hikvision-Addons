# Home Assistant Add-on: Hikvision SDK for Door Intercoms

## What can it do? 
- It listen for events: callstatus/motion detection/door unlocked/tamper alarm/dimissed alarm
- It can open a door, usefull for older devices where ISAPI is not possible, when port 80 is blocked
- It can send a callsignal command, like answer/reject,hangup ... verry usefull if you have for example a zigbee door sensor, if you open the door by hand, you can drop the ring signal on the indoor stations/or stop hikconnect devices ringing :-)

## Get started

Open your Home Assistant instance and add an custom repository for your add-ons: https://github.com/pergolafabio/Hikvision-SDK-Addon

PS: On first start of the Addon, its possible that your doorstation gets stuck, sometimes a reboot is needed, because this Add-on will download the complete backlog... its only the first time

## Gonfiguration of the Add-On

````
    "ip": "192.168.0.70" # The IP of your outdoor station
    "ip_indoor": "192.168.0.71", # In case you have an indoor Panel, usefull for the callsignal command, more info below
    "username": "admin", # The username of your outdoor station
    "password": "password" # The password of your outdoor station
    "bearer" : "YOURLONGBEARERTOKEN" # Bearer token, more info below
    "url_states": "http://localhost:8123/api/states/" # The URL of your HA instance, to update the sensors below
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

## Open a door

To open a door, we need to send a stdin message to the add-on, it can be used with this service below, use as input: unlock1 OR unlock2, depending if you have 2 output relays on your doorstation.
In below example, a53439b8_hikvision_sdk is the addon name, its possible that its different for you

````
service: hassio.addon_stdin
data:
  addon: a53439b8_hikvision_sdk
  input: unlock1
````

## Callsignal

The callsignal service is usefull to reject the call, i personally use it with a zigbee sensor at my door... When someone pressed the doorbutton, if i open the door by hand without pickup up, the below service rejects the call, and all indoor stations stop ringing, including the hikconnect devices.

Available commands are: "request, cancle, answer, reject, bellTimeout, hangUp, deviceOnCall" ... no idea what they do, i only use "reject". 
Again, "a53439b8_hikvision_sdk" is an example of the add-on name, it can be different for you...

````
service: hassio.addon_stdin
data:
  addon: a53439b8_hikvision_sdk
  input: reject
````

## Bearer token

I make use of a REST API command to update the template sensors, so you need to create also a BEARER token, its a verry long string

Instructions:
- To Generate Long-lived Access Token, first login into your Home Assistant
- On the bottom left, in the menu area, click the “Profile” button:
- Scroll down the profile page until the bottom. You will find a section for Long-Lived Access Tokens. Click “Create Token” button.
- Give your Token a name, so it's easy to manage and understand where and for what it's being used for. Click “OK” button to confirm.
- The Long-lived access token will be generated. Make sure you copy the token value and past it in your application where you need it. You wont be able to see this value again, in case you lose it you will need to create another token.

PS: My local instance runs on http, so if your doesnt, make sure you change it in the 'url_states'

Creds:
The add-on is based on this script : https://github.com/laszlojakab/hikvision-intercom-python-demo
