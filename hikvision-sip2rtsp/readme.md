# Home Assistant Add-on: SIP2RTSP

## Background info:

Hikvision intercom devices have the ability to register on a PBX, but the disadvantage of using the SIP setting on the device:

- When PBX is down => you miss the call :-)
- When connected to a PBX , Hikconnect cloud doesnt work anymore
- No video before pickup anymore on the indoor panels, so you dont see who is calling, quite annoying!!

There is another way!!!

In asterisk you can define an TRUNK, to register on the primary indoor station, Asterisk will act as an second indoor extension... so the call comes in, your first indoor stations starts ringing, and will forward the call to Asterisk
One problem tough, for some reason the video is not visible on the softphones, that's why I crated this addon...
Advantages:

- Hikconnect cloud, still works!
- Still video on your indoor panels!!! Most important one
- If this addon is down, the intercom still works as we register it as an extension
- You dont need access to the outdoor station, usefull for people living in appartment with no access to outdoor station.
- You dont need to use the Hikconnect app anymore, you can use your own softphone
- All local
- Verry nice intergations possible, you can even pickup/answer the call with a Lovelace SIP card!! Freaking nice! :-)  https://github.com/TECH7Fox
- It will provide you call sensors based on sip, using the asterisk integration or use my SDK addon instead
- Opening door also works by sending '#' during call with a softphone

## Install:

Copy over the file sip2rtsp.cfg to your config folder, change it according to your needs and start the add-on
https://github.com/pergolafabio/Hikvision-Addons/blob/main/hikvision-sip2rtsp/sip2rtsp.cfg

## Trunk example for Asterisk


As I told before, this addon registers on the indoor station, you need to add it first manually with the IVMS software
For serial use: Q12345678, for No: 5, enter "Admin" password, the the IP is your HA instance running the addon... I used 5, because maybe there al already users with 4 indoor stations, so this will be the 5th :-)

In below example, 192.168.0.71 is my primary indoor panel, 10000000005 is actually the number 5 you entered in IVMS

![Ivms](ivms.PNG)

```
[mytrunk-auth]
type=auth
auth_type=userpass
password=XXXX
username=10000000005
 
[mytrunk-aor]
type=aor
contact=sip:192.168.0.71:5065

[mytrunk-registration]
type=registration
outbound_auth=mytrunk-auth
server_uri=sip:192.168.0.71:5065
client_uri=sip:10000000005@192.168.0.71:5065
retry_interval=10
contact_user=10000000005
expiration=600
 
[mytrunk]
type=endpoint
context=default
disallow=all
allow=ulaw,alaw
allow=h264,vp8
outbound_auth=mytrunk-auth
aors=mytrunk-aor
rewrite_contact=yes
from_domain=mydomain.com
 
[mytrunk]
type=identify
endpoint=mytrunk
match=192.168.0.71
```

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

#### Setup this in confbrifge.conf:

[admin_user]
type=user
marked=no
wait_marked=no
end_marked=yes
admin=yes
music_on_hold_when_empty=no
quiet=yes
dtmf_passthrough=yes

[default_user]
type=user
marked=no
wait_marked=yes
end_marked=yes
admin=no
music_on_hold_when_empty=no
quiet=yes
dtmf_passthrough=yes
;answer_channel=no

[marked_user]
type=user
marked=yes
wait_marked=no
end_marked=yes
admin=no
music_on_hold_when_empty=no
quiet=yes
dtmf_passthrough=yes
startmuted=yes

[myconferenceroom]
type=bridge
max_members=10
video_mode=first_marked


```
## Creds

https://github.com/larkguo/sip2rtsp
