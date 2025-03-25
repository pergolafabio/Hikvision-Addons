# Setup Advanced Camera Card to use two way audio with Hikvision doorbells


## Background info:

Our hikvision devices do support SIP, but SIP knowledge is necessary, its not always easy to setup a PBX like Asterisk, but there is another away!
Most cameras/doorbells do have a speaker/microphone, so two way audio (talk-back) can be activated, they all use a different protocol, in case of Hikvision its ISAPI

Somewhere begin 2023 this ISAPI protocol was inserted in the go2rtc addon, the advanced camera card offers a card with microphone support!! So that means we can use an camera entity in HA and we can actually speak to the person at the doorbell.

## Advantages:

- No need to setup complex SIP
- Answer the call with HA or companion app
- Talk to the person at the doorbell, whenever you want, no need to initiate a call first
- With go2rtc you can send streams/music to your Doorbell :-)
- ....

## Prerequisites:
- Home Assistant! :-)
- Advanced Camera Card: https://github.com/dermotduffy/advanced-camera-card
- Go2rtc Addon: https://github.com/AlexxIT/hassio-addons

## Get started:

Install the go2rtc Addon, this addon is needed, the once in core doesnt work, since you cant customize the streams (isapi support)

## Step 1: go2rtc Add-On configuration

A simple go2rtc.yml configuration to add the doorbell with ISAPI support:
IMPORTANT: HTTPS is needed! to have MIC support, i use nginx to access my instance, if you dont use nginx, make sure to enable tls in below config
If go2rtc setup is configured, you should be able to view the stream by browsing to this page https://user:pass@yourdomain:1985 (then click on links and then: "video+audio+microphone = two way audio from camera", test the stream to test your go2rtc config)

More info here:

https://github.com/AlexxIT/go2rtc?tab=readme-ov-file#module-webrtc

https://github.com/AlexxIT/go2rtc?tab=readme-ov-file#source-isapi

```
streams:
  deurbel:
    - rtsp://admin:xxx@192.168.0.70:554/Streaming/Channels/101
    - isapi://admin:xxx@192.168.0.70:80/
api:
  listen: ":1984"    # default ":1984", HTTP API port ("" - disabled)
  username: "user"  # default "", Basic auth for WebUI
  password: "pass"   # default "", Basic auth for WebUI
  origin: "*"        # default "", allow CORS requests (only * supported)
  #tls_listen: ":1985" # default "", enable HTTPS server
  #tls_cert: /ssl/fullchain.pem
  #tls_key: /ssl/privkey.pem

```
## Step 2: Advanced Card configuration

Step 1 was the hardest, now the easy part, I quickly created a card configuration, hided some unneeded buttons that i dont use, ...

IMPORTANT: When there is an incoming call from your doorbell, the outside speaker is in use, when you activate the two way audio with the card, it doesnt pass the audio and the ringing just continues...
With my Hikvision Add-On you can first "answer" the call and then "hangup", and then start talking with twowayaudio, you can see i added an "element" section below, where i added an extra "phone" button. The "answer" + "hangUp" i send to my INDOOR station... You can also just send the "reject" instead, but that makes a "beep beep beep" tone at your outdoor
For people without an indoor station, some people say confirmed that sending "hangup" is enough to stop the ringing, you should test this...

So the "phone" button activates some services:
- First send "answer" + "hangUp"  commands, to stop the real call and to make the speaker idle again
- Lastly then it unmutes the microphone (start two way audion) and unmutes the card.
- Offcourse change the entity names in the elements section for your indoor/outdoor station. I also added a hold action to open the door, also change the entity name there too... Also added some delays, maybe its not needed or maybe more, this something you can test to make it better

If you send the "answer" command and you notice error 29 in the log on a real call, this means that your device is NOT connected to Hikconnect, seems for the answer command to work, it needs internet connection... It thats not possible, you can use the "reject" command instead!

The "phone-hangup" button:
- Mutes the microphone
- I also send the ISAPI command to close the audio channel to the OUTDOOR station... This one is needed also, cause if the card is still open, seems the second call doesnt activate the microphone/speaker anymore, somehow the card doesnt really close the audiochannels when muting the microphone.. so forcing to close  the audiochannel when you hangup does the trick! 

So in below example screenshot, the first 3 icons are just for starting two way audi / mute / unmute, BUT without a real call!! When you actually have an incoming doorbell ring, you need to use the phone/hangup buttons.

IMPORTANT: If you are missing the first icon, the microphone button, that means your go2rtc addon is not working correctly, remember, https and a valid ssl is needed!

![Ivms](advanced.card.png)

```
        - type: custom:advanced-camera-card
          cameras:
            - live_provider: go2rtc
              go2rtc:
                url: https://yourdomain.com:1985
                stream: deurbel
                modes:
                  - mse
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
              iris:
                enabled: false
              camera_ui:
                enabled: false
          live:
            microphone:
              always_connected: true
              mute_after_microphone_mute_seconds: 90
            auto_mute: []
            auto_unmute: []
            controls:
              builtin: true
              title:
                mode: none
            layout:
              fit: fill
          elements:
            - type: custom:advanced-camera-card-menu-icon
              icon: mdi:volume-high
              tap_action:
                - action: custom:advanced-camera-card-action
                  advanced_camera_card_action: unmute
            - type: custom:advanced-camera-card-menu-icon
              icon: mdi:volume-off
              tap_action:
                - action: custom:advanced-camera-card-action
                  advanced_camera_card_action: mute
            - type: custom:advanced-camera-card-menu-icon
              icon: mdi:phone
              tap_action:
                - action: call-service
                  service: button.press
                  data:
                    entity_id: button.ds_kh9510_answer_call
                - action: call-service
                  service: button.press
                  data:
                    entity_id: button.ds_kh9510_hangup_call
                - action: custom:advanced-camera-card-action
                  advanced_camera_card_action: sleep
                  duration:
                    ms: 200
                - action: custom:advanced-camera-card-action
                  advanced_camera_card_action: unmute
                - action: custom:advanced-camera-card-action
                  advanced_camera_card_action: microphone_unmute
            - type: custom:advanced-camera-card-menu-icon
              icon: mdi:phone-hangup
              tap_action:
                - action: custom:advanced-camera-card-action
                  advanced_camera_card_action: microphone_disconnect
                - action: custom:advanced-camera-card-action
                  advanced_camera_card_action: mute
                - action: call-service
                  service: text.set_value
                  data:
                    entity_id: text.ds_kd8003_isapi_request
                    value: PUT /ISAPI/System/TwoWayAudio/channels/1/close
            - type: custom:advanced-camera-card-menu-icon
              icon: mdi:door-open
              hold_action:
                - action: call-service
                  service: switch.turn_on
                  data:
                    entity_id: switch.ds_kd8003_door_relay_0
          dimensions:
            aspect_ratio_mode: static
            aspect_ratio: '4:3'
          status_bar:
            style: none
```

Have FUN :-)

## Donations
 Like my work? You can always [send me a donation](https://paypal.me/pergolafabio).
