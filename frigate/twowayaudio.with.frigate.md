# Setup Frigate to use two way audio with Hikvision doorbells


## Background info:

Our hikvision devices do support SIP, but SIP knowledge is neccasry, its not always easy to setup a PBX like Asterisk, but there is another away!
Most cameras/doorbells do have a speaker/microphone, so two way audio (talk-back) can be activated, they all use a different protocol, in case of Hikvision its ISAPI
Somewhere begin 2023 this ISAPI protocol was inserted in the go2rtc addon, Frigate is an NVR system that can be used in combination with the go2rtc addon... 
Frigate also offers an lovelace sip card, and YES, with microphone support!! So that means we can use an camera entity in HA and we can actually speak to the person at the doorbell.
I think this Frigate card is the first card, that has microphone support 


Advantages:

- No need to setup complex SIP
- Aswner the call with HA companion app
- Talk to the person at the doorbell, whenever you want, no need to initiate a call first
- With go2rtc you can send streams/music to your Doorbell :-)
- Frigate supports person detection, so you can already start talking before the postman actually pressed the doorbutton! :-)
- ....

## Prerequisites:
- Home Assistant! :-)
- Frigate Add-on: https://github.com/blakeblackshear/frigate-hass-addons
- Frigate Hass Integration: https://github.com/blakeblackshear/frigate-hass-integration
- Frigate Hass Card: https://github.com/dermotduffy/frigate-hass-card
- MQTT Broker

## Get started:

Install the Frigate Addon, as i told earlier, this Frigate addon uses in background the go2rtc addon. BUT, the version included is still 1.2, ISAPI was introduced in go2rtc since version 1.3.2, so we need to configure the Frigate Addon to use the latest version of go2rtc, this time of writing i used 1.6.2. 
Here are the instructions to use a custom version of go2rtc: https://docs.frigate.video/configuration/advanced/#custom-go2rtc-version

When starting the Frigate Add-on you should see this if you configured it correctly:

```
2023-08-10 12:51:48.188302372  [WARN] Using go2rtc binary from '/config/go2rtc' instead of the embedded one
2023-08-10 12:51:48.188310430  [INFO] Starting go2rtc...
2023-08-10 12:51:48.311927197  14:51:48.311 INF go2rtc version 1.6.2 linux/amd64
```

## Step 1: Frigate configuration

A simple frigate.yml configuration to add the doorbell with ISAPI support:

```
mqtt:
  enabled: True
  host: IP
  user: username
  password: pass

cameras:
  Doorbell:
    ffmpeg:
      inputs:
        - path: rtsp://admin:XXXXXXXX@192.168.0.70:554/Streaming/Channels/101

go2rtc:
  streams:
    Doorbell:
      - rtsp://admin:XXXXXXXX@192.168.0.70:554/Streaming/Channels/101
      - isapi://admin:XXXXXXXX@192.168.0.70:80/

```
First of all, check if ISAPI already works, you can expose/enable port 1984 in the Frigate Add-on, afterwards you can surf to to https://mydomain:1984 or http://IP:1984
You should see the camera there, with also a "links" command, click on it, at the bottom you should see: "video+audio+microphone = two way audio from camera"

In order to test, chrome needs https with valid domain to give permissions to the camera, to use with http, you can apply this hack:
https://stackoverflow.com/questions/52759992/how-to-access-camera-and-microphone-in-chrome-without-https

OR you can also use this button: "external WebRTC viewer", that one creates a valid https link for you

## Step 2: Frigate card configuration

Step 1 was the hardest, now the easy part, I quickly created a card configuration, hided some unneeded buttons that i dont use, ...

IMPORTANT: When there is an incoming call from your doorbell, the outside speaker is in use, when you activate the two way audio with the card, it doesnt pass the audio!
With my Hikvision Add-On you can first "answer" the call, and then start talking, you can see i added an "element" section below, where i added an extra "phone" button. 
The phone buttons activates 2 services, first it answers the call, and then it unmutes the microphone! Offcourse change the entity in the elements section

![Ivms](frigate.png)

Have FUN :-)

```
        - type: custom:frigate-card
          cameras:
            - camera_entity: camera.doorbell
              live_provider: go2rtc
              go2rtc:
                modes:
                  - webrtc
          menu:
            style: outside
            position: bottom
            buttons:
              microphone:
                enabled: true
                type: toggle
              screenshot:
                enabled: false
              download:
                enabled: false
              fullscreen:
                enabled: false
              snapshots:
                enabled: false
              timeline:
                enabled: false
              media_player:
                enabled: false
              clips:
                enabled: false
              live:
                enabled: false
              cameras:
                enabled: false
              frigate:
                enabled: false
              camera_ui:
                enabled: false
          live:
            auto_mute: never
            controls:
              builtin: false
              title:
                mode: none
            layout:
              fit: fill
          elements:
            - type: custom:frigate-card-menu-icon
              icon: mdi:phone
              tap_action:
                - action: call-service
                  service: button.press
                  service_data:
                    entity_id: button.ds_kh9510_answer_call
                - action: custom:frigate-card-action
                  frigate_card_action: microphone_unmute

          dimensions:
            aspect_ratio_mode: static
            aspect_ratio: '16:9'
```



