# Home Assistant Add-on: Hikvision SDK for Door Intercoms
## What can it do? 
- It listen for events: callstatus/motion detection/door unlocked
- It can open a door, usefull for older devices where ISAPI is not possible, when port 80 is blocked

## Alert

The supplied "lib" from hikvision, only runs on i386 / amd64, so it will not work on Raspberry...
https://www.hikvision.com/nl/support/download/sdk/

## Get started

Open your Home Assistant instance and add an custom repositoryfor your add-ons: https://github.com/pergolafabio/Hikvision-SDK-Addon 

First of all, create the template sensors in your yaml configuration, like below:
When door is opened by key/badge, or when the doorbell is ringing, or motion detected, or tamper alarm... the state of the sensors below are "on" for 2 seconds

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
````
To open a door, we need to send a stdin message to this docker add-on, it can be used with this service below, use as input: unlock1 OR unlock2, depending if you have 2 output relays on your doorstation.

````
service: hassio.addon_stdin
data:
  addon: a53439b8_hikvision_sdk
  input: unlock1
````

After adding this addon as a custom repository, define the options for your hikvision door intercom... 

Ip & username & password, are the values from your outdoor station...

````
    "ip": "192.168.0.75",
    "username": "admin",
    "password": "password", 
    "bearer" : "YOURLONGBEARERTOKEN",
    "url_states": "http://localhost:8123/api/states/",
    "sensor_door" : "hikvision_door",
    "sensor_callstatus" : "hikvision_callstatus"
    "sensor_motion" : "hikvision_motion"
````	
I make use of a REST API command to update the template sensors, so you need to create also a BEARER token, its a verry long string

Instructions:
- To Generate Long-lived Access Token, first login into your Home Assistant
- On the bottom left, in the menu area, click the “Profile” button:
- Scroll down the profile page until the bottom. You will find a section for Long-Lived Access Tokens. Click “Create Token” button.
- Give your Token a name, so it's easy to manage and understand where and for what it's being used for. Click “OK” button to confirm.
- The Long-lived access token will be generated. Make sure you copy the token value and past it in your application where you need it. You wont be able to see this value again, in case you lose it you will need to create another token.

PS: My local instance runs on http, so if your doesnt, make sure you change it in the 'url_states'

The add-on is based on this script : https://github.com/laszlojakab/hikvision-intercom-python-demo
