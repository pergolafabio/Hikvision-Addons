# Home Assistant Add-on: SIP2RTSP

## Background info:

For people using my OpenSips addon, seems video is not forwarded, so i created this new extra addon, this creates an extension with video...
In asterisk its possible to create an conf call, the idea is to invite this UAC user in the call to see video

## Install:

Copy over the file sip2rtsp.cfg to your config folder, change it according to your needs and start the add-on
https://github.com/pergolafabio/Hikvision-Addons/blob/main/hikvision-sip2rtsp/sip2rtsp.cfg

## Dialplan example

You can create an diaplan with conference room, lets say the doorbell calls "777" with Originate you can invite the sip2rtsp (7000)  user into the conference!
Enjoy the RTSP stream from the camera :-)

```
exten => 777,1,NoOp()
 same => n,Progress()
 same => n,Wait(1) 
 same => n,Originate(PJSIP/7000,exten,default,888,1,,aC(ulaw,alaw,h264)c(7000)n(Hikvision))
 same => n,Originate(PJSIP/6000,exten,default,999,1,,aC(ulaw,alaw,h264)c(6000)n(Fabio)) 
 same => n,ConfBridge(1,myconferenceroom,admin_user)
 
 
exten => 888,1,NoOp()
 same => n,Progress()
 same => n,Wait(1) 
 same => n,ConfBridge(1,myconferenceroom,admin_user)

exten => 999,1,NoOp()
 same => n,Progress()
 same => n,Wait(1) 
 same => n,ConfBridge(1,myconferenceroom,marked_user)
 
 
#### extension sip2rtsp example:

[7000]
type=endpoint
context=default
disallow=all
allow=ulaw,alaw
allow=h264,vp8
auth=auth7000
aors=7000
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes
direct_media=yes
max_audio_streams=10
max_video_streams=10
from_domain=mydomain.com

[auth7000]
type=auth
auth_type=userpass
password=1234
username=7000
 
[7000]
type=aor
max_contacts=1
remove_existing=yes
remove_unavailable=yes
 
```

