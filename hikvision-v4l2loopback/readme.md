# Home Assistant Add-on: V4l2Loopback with intergrated LinphoneC terminal client

## Background info:

For people using my OpenSips addon, seems video is not forwarded, so i created this new extra addon, this creates an virtual "/dev/video0" loopback device...
You can insert aftewards any RTSP stream with ffmpeg, options are mandatory, i have included the examples:

- reg_proxy: The PBX to where the linphone client is registering on...
- reg_identity: The AOR format
- username: Username of the extension on the PBX
- passwd: Password of the extension
- rtsp: The ffmpeg string to inject RTSP into "/dev/video0" 

Aftewards, you can call the extension and see the video, because linphonec is staring with auto-answer enabled...

## Important

This addon is loading a Kernel module at the start with this command: "insmod /app/v4l2loopback.ko exclusive_caps=1 devices=1"
The "v4l2loopback" is not part of HassOS, so thats why i compiled a test HassOS build with Buildroot and v4l2enabled, afterwards i copied over the .ko file...
Its based on kernel 5.15.41 (HassOS 8.1) and will only work on this version only... i have a vermagic command ready to change the version (untested) ... 
But i have asked developers to make v4l2loopback be part of HassOS, this was approved and will be included in next OS release, so the isnmod should not be needed anymore later...

## Dialplan example

You can create an diaplan with conference room, lets say the doorbell calls "777" with Originale you can invite the linphonec user into the conference and yourself...

```
exten => 777,1,NoOp()
 same => n,Progress()
 same => n,Wait(1) 
 same => n,Originate(PJSIP/1234,exten,default,777,1,,aC(ulaw,alaw,h264)c(1234)n(Doorbell))
 same => n,Originate(PJSIP/6000,exten,default,888,1,,aC(ulaw,alaw,h264)c(6000)n(Fabio)) 
 same => n,ConfBridge(1,myconferenceroom,admin_user)
 
 
exten => 777,1,NoOp()
 same => n,Progress()
 same => n,Wait(1) 
 same => n,ConfBridge(1,myconferenceroom,admin_user)

exten => 888,1,NoOp()
 same => n,Progress()
 same => n,Wait(1) 
 same => n,ConfBridge(1,myconferenceroom,marked_user)
 
```

