# Home Assistant Add-on: Hikvision SIP2RTSP for Asterisk

IMORTANT: To use this add-on, you need to have a working Asterisk server, or any PBX of your choise... This add-on is nothing more then an extension thay you can call with auto-answer enabled, to display the RTSP feed, below i have added some info about how to setup Asterisk... 
Here is a nice addon for Asterisk to play with: https://github.com/TECH7Fox/asterisk-hass-addons

## Background info:

Hikvision intercom devices have the ability to register on a PBX, but the disadvantage of using the SIP setting on the device:

- When PBX is down => you miss the call :-)
- When connected to a PBX , Hikconnect cloud doesnt work anymore
- No video before pickup anymore on the indoor panels, so you dont see who is calling, quite annoying!!

There is another way!!!

In asterisk you can define an TRUNK, to register on the primary indoor station, Asterisk will act as an second indoor extension... so the call comes in, your first indoor stations starts ringing, and will forward the call to Asterisk
One problem tough, for some reason the video is not visible on the softphones, that's why I created this addon... , just to have video in the call on the softphones...

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

## How to register an extension

As I told before, this addon registers on the indoor station, you need to add it first manually with the IVMS software
For serial use: Q12345678, for No: 5, enter "Admin" password, the the IP is your HA instance running the addon... I used 5, because maybe there al already users with 4 indoor stations, so this will be the 5th :-)

In below example, 192.168.0.71 is my primary indoor panel, 10000000005 is actually the number 5 you entered in IVMS, 192.168.0.17 is HA running Asterisk


![Ivms](ivms.PNG)

PS: On some indoor panels, when registering the trunk you get an 404/401 error... some panels really need to have the regXML body part, therefore you can run the below script in background, it will send the regXML part, runs on port 5061, but the invite on indoor panel is always hardcoded, so it goes back to port 5060, where yo u have asterisk running. The script needs to be running the whole time, so start it with an automation upon boot HA, and use this shell_command below, so the script runs the whole time in background... its doing an reregister every 900 sec.

https://gist.github.com/pergolafabio/9964ff2c2750fba447c5ca63382f4600

```
hikvision_sip: nohup python3 /config/python_scripts/hikvision_register.py --ip 192.168.0.17 --domain 192.168.0.71 --username 10000000005 --extension 10000000005 --name Asterisk --password XXX $1 > /dev/null 2>&1 &

- alias: Register hikvision 
  initial_state: 'off'
  trigger:
    - platform: homeassistant
      event: start
  action:
    - service: shell_command.hikvision_sip
```

Example regXML that is needed in the register packet:

```
<regXML>
<version>V2.0.0</version>
<regDevName>Asterisk</regDevName>
<regDevSerial>Q12345678</regDevSerial>
<regDevMacAddr>00:0c:29:12:12:12</regDevMacAddr>
</regXML>
```
## Asterisk trunk setup
```
####  Use this AUTH TRUNK when you dont need to run the script above!!
#### Setup this in pjsip_custom.conf:

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

####  Use this IP TRUNK when you need the regsister script, so it gets the invite send to port 5060

[hikvision]
type=aor
contact=sip:10000000005@192.168.0.71:5060

[hikvision]
type=endpoint
context=default
disallow=all
allow=ulaw,alaw
allow=h264,vp8
aors=hikvision
direct_media=no

[hikvision]
type=identify
endpoint=hikvision
match=192.168.0.71

```

## Dialplan example using conference bridge
# Example 1: With use of regular softphones: make for example 2 extensions, on incoming call of the trunk, the group will be called with members 6000 and 6001, but no video injected with this example

```

#### Setup this in extensions.conf:

exten => 10000000005,1,NoOp() 
 same => n,Progress()
 same => n,Set(CALLERID(num)=10000000005)
 same => n,Set(CALLERID(name)=DS-KD8003) 
 same => n,Set(__DYNAMIC_FEATURES=door)
 same => n,Set(DIALGROUP(mygroup,add)=PJSIP/6000)
 same => n,Set(DIALGROUP(mygroup,add)=PJSIP/6001)  
 same => n,Dial(${DIALGROUP(mygroup)},40)
 ```
 
# Example 2: When using a conference, you can inject the the RTSP extension to the call, in example below its user 7000, so the doorbell starts a conference, with the originate you can invite 7000 and 6000 to the call... this is also verry usefull when using the SIP Lovelace card, because this card gets unregistered of you close HA... this way you can join the call to pickup the doorbell

```
#### Setup this in extensions.conf:

exten => 10000000005,1,NoOp()
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
 
 
#### Setup this in pjsip_custom.conf:

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
