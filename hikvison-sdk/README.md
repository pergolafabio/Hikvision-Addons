# Home Assistant Add-on: Hikvision SDK

The Hikvision SDK add-on for Home Assistant... This add-on is based on this script : https://github.com/laszlojakab/hikvision-intercom-python-demo

## Alert

The supplied "lib" from hikvision, only runs on i386 / amd64, so it will not work on Raspberry, this addon is based on amd64 lib, if you need i386, download the lib from the Hikvision SDK website and change it
https://www.hikvision.com/nl/support/download/sdk/
It also runs on specific OS only, no Alpine, thats why i used: FROM python:3.7-slim

## Get started

Open your Home Assistant instance and add an custom repositoryfor your add-ons: https://github.com/pergolafabio/Hikvision-SDK-Addon 

First of all, create 2 template sensors in your yaml configuration, like below:
When door is opened by key/badge, or when the doorbell is ringing, the state of the sensors below are "on" for 2 seconds

````
  - platform: template
    sensors:
      hikvision_door:
        value_template: "off"
      hikvision_callstatus:
        value_template: "off"
````

After adding this addon as a custom repository, define the options for your hikvision door intercom... Default values are:

````
    "ip": "192.168.0.75",
    "username": "admin",
    "password": "password", 
    "bearer" : "YOURLONGBEARERTOKEN",
    "url_states": "http://localhost:8123/api/states/",
    "sensor_door" : "hikvision_door",
    "sensor_callstatus" : "hikvision_callstatus"
````	
I make use of a REST API command to update the template sensors, so you need to create also a BEARER token, its a verry long string

Instructions:
- To Generate Long-lived Access Token, first login into your Home Assistant
- On the bottom left, in the menu area, click the “Profile” button:
- Scroll down the profile page until the bottom. You will find a section for Long-Lived Access Tokens. Click “Create Token” button.
- Give your Token a name, so it's easy to manage and understand where and for what it's being used for. Click “OK” button to confirm.
- The Long-lived access token will be generated. Make sure you copy the token value and past it in your application where you need it. You wont be able to see this value again, in case you lose it you will need to create another token.

PS: My local instance runs on http, so if your doesnt, make sure you change it in the 'url_states'
