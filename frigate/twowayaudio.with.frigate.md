# Setup Frigate to use two way audio with Hikvision doorbells


## Background info:

Our hikvision devices do support SIP, but SIP knowledge is necessary, its not always easy to setup a PBX like Asterisk, but there is another away!
Most cameras/doorbells do have a speaker/microphone, so two way audio (talk-back) can be activated, they all use a different protocol, in case of Hikvision its ISAPI

Somewhere begin 2023 this ISAPI protocol was inserted in the go2rtc addon, Frigate is an NVR system that can be used in combination with the go2rtc addon... 
Frigate also offers an lovelace sip card, and YES, with microphone support!! So that means we can use an camera entity in HA and we can actually speak to the person at the doorbell.
I think this Frigate card is the first card with microphone support! 


## Advantages:

- No need to setup complex SIP
- Answer the call with HA or companion app
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

Install the Frigate Addon (at least 0.13), this Frigate addon uses in background the go2rtc addon.

## Step 1: Frigate Add-On configuration

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
First of all, check if ISAPI already works, you can expose/enable port 1984 in the Frigate Add-on, afterwards you can surf to to http://mylocalip:1984
You should see the camera there, with also a "links" command, click on it, at the bottom you should see: "video+audio+microphone = two way audio from camera"

Chrome doesnt allow microphone support if you visit that webpage with http, but you can apply this hack:
https://stackoverflow.com/questions/52759992/how-to-access-camera-and-microphone-in-chrome-without-https

OR you can also use this button: "external WebRTC viewer", that one creates a valid https link for you

## Step 2: Frigate Hass Integration

When the Add-on is running and all working well, install the Frigate integration, MQTT is necessary. After the integration is finished, the camera entity will be created in HA, that you need to use with the Frigate Hass Card

## Step 3: Frigate Hass Card configuration

Step 1 was the hardest, now the easy part, I quickly created a card configuration, hided some unneeded buttons that i dont use, ...

IMPORTANT: When there is an incoming call from your doorbell, the outside speaker is in use, when you activate the two way audio with the card, it doesnt pass the audio!
With my Hikvision Add-On you can first "answer" the call and then "hangup", and then start talking, you can see i added an "element" section below, where i added an extra "phone" button. The "answer" + "hangUp" i send to my indoor station... You can also just send the "reject" instead, but that makes a "hanngup" tone at your outdoor

So the phone buttons activates 4 services, first it "answer" + "hangUp"  the call, and then it unmutes the microphone (start two way audion) and unmutes the card .Offcourse change the entity names in the elements section for your indoor/outdoor station. I also added a hold action to open the door, also change the entity name there too...

If you send the "answer" command and you notice error 29 in the log on a real call, this means that your device is NOT connected to Hikconnect, seems for the answer command to work, it needs internet connection... It thats not possible, you can use the "reject" command instead!

![Ivms](frigate.png)

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
              builtin: true
              title:
                mode: none
            layout:
              fit: fill
          elements:
            - type: custom:frigate-card-menu-icon
              icon: mdi:volume-high
              tap_action:
                - action: custom:frigate-card-action
                  frigate_card_action: unmute
            - type: custom:frigate-card-menu-icon
              icon: mdi:volume-off
              tap_action:
                - action: custom:frigate-card-action
                  frigate_card_action: mute
            - type: custom:frigate-card-menu-icon
              icon: mdi:phone
              tap_action:
                - action: call-service
                  service: button.press
                  service_data:
                    entity_id: button.ds_kh9510_answer_call
                - action: call-service
                  service: button.press
                  service_data:
                    entity_id: button.ds_kh9510_hangup_call
                - action: custom:frigate-card-action
                  frigate_card_action: unmute
                - action: custom:frigate-card-action
                  frigate_card_action: microphone_unmute
            - type: custom:frigate-card-menu-icon
              icon: mdi:phone-hangup
              tap_action:
                - action: custom:frigate-card-action
                  frigate_card_action: microphone_mute
            - type: custom:frigate-card-menu-icon
              icon: mdi:door-open
              hold_action:
                - action: call-service
                  service: switch.turn_on
                  service_data:
                    entity_id: switch.ds_kd8003_door_relay_0

          dimensions:
            aspect_ratio_mode: static
            aspect_ratio: '16:9'
```

Have FUN :-)

## Donations
 Like my work? You can always [send me a donation](https://paypal.me/pergolafabio).
