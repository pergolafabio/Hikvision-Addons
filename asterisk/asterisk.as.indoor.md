# Setup Asterisk as inbound trunk like an Hikvision indoor extension


## Background info:

Hikvision intercom devices have the ability to register on a PBX, but the disadvantages of using the SIP setting on the device:

- When PBX is down => you miss the call :-)
- When connected to a PBX , Hikconnect cloud doesnt work anymore
- No video before pickup anymore on the indoor panels, so you dont see who is calling, quite annoying!!

There is another way!!!

In asterisk you can define an TRUNK, to register on the primary indoor station, Asterisk will act then as an indoor extension just like a real indoor device... so the call comes in, your first indoor stations starts ringing, and will forward the call to Asterisk.
For some reason the video is not forwarded... no idea why ... that's why I created this workaround to have video in the call on the softphones...

Advantages:

- Hikconnect cloud, still works!
- Still video on your indoor panels! Most important one
- If Asterisk is down, the intercom + indoor station still works as we register it as an extension
- You dont need access to the outdoor station, usefull for people living in appartment with no access to outdoor station.
- You dont need to use the Hikconnect app anymore, you can use your own softphone of choice
- All local!
- Verry nice intergations possible, you can even pickup/answer the call with a Lovelace SIP card!! Freaking nice! :-)  https://github.com/TECH7Fox/sip-hass-card
- Opening door also works by sending '#' during call with a softphone (enable "dtmf sip-info" on your softphone client), or use feature codes, see more below

## Get started:

Setup an asterisk PBX, i use the one from Techfox, it already includes the RTSP App, that we need in this approach. https://github.com/TECH7Fox/asterisk-hass-addons
If you want to compile your onw Asterisk, make sure to include this app: https://github.com/tommyjlong/app_rtsp_sip

## Asterisk configuration

As I told before, you can use Asterisk to register as a trunk on your primary indoor panel... 

#### Option 1 based on newer indoor panels
On same indoor panels you can already the extension with a SN.. for serial use: Q12345678, for No: 5, enter a password, the the IP is your Asterisk  instance running the addon... 
In below example, 192.168.0.71 is my primary indoor panel, 10000000005 is actually the number 5 you entered in IVMS, 192.168.0.17 is HA running Asterisk
Some indoor panels dont have the option to add extensions, then try without it, just use the trunk setup below... if you receive an 404 or 401 error when debugging sip, proceed to option 2, and skip this trunk setup... I always use the tool "sngrep", you can install it in the SSH addon with the command "apk add sngrep"


![Ivms](ivms.png)

Below is the trunk you need to define in Asterisk, make sure the password matches, now restart Asterisk, and see if if the Asterisk can succesfull register

```
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
```
#### Option 2 based on older indoor panels

On some indoor panels you are not able to add the SN with ivms, when registering the trunk you get an 404/401 error... the SN is mandatory, and Asterisk is not able to send the XML.. Use below script instead...it will send the regXML part, it runs on port 5061, but the invite on indoor panel is always hardcoded, so it goes back to port 5060, where yo u have asterisk running. 
The script needs to be running the whole time, so start it with an automation upon boot HA, and use this shell_command below.. its doing an reregister every 900 sec.


[hikvision_register.py](hikvision_register.py)

Try it fist from a putty console, to see it it works, afterwards you can use below shellcommand with an automation.


```
## Test first this command:
python3 /config/hikvision_register.py --ip 192.168.0.17 --domain 192.168.0.71 --username 10000000005 --extension 10000000005 --name Asterisk --password XXX
```
Use this below in HA
```
# Shell command:
hikvision_sip: nohup python3 /config/hikvision_register.py --ip 192.168.0.17 --domain 192.168.0.71 --username 10000000005 --extension 10000000005 --name Asterisk --password XXX $1 > /dev/null 2>&1 &

# Automation:
- alias: Register hikvision 
  initial_state: 'on'
  trigger:
    - platform: homeassistant
      event: start
  action:
    - service: shell_command.hikvision_sip
```

Example regXML that is needed in the register packet, its part of the script in the register header...

```
<regXML>
<version>V2.0.0</version>
<regDevName>Asterisk</regDevName>
<regDevSerial>Q12345678</regDevSerial>
<regDevMacAddr>00:0c:29:12:12:12</regDevMacAddr>
</regXML>
```

Use the trunk below, based on IP auth, this one is different, there is no need for user/pass authentication now, since the script is doing the auth

```
#### Setup this in pjsip_custom.conf:

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

## Simple Dialplan for Asterisk

#### Example 1: 
Using Linphone as a free service, the call comes in on '10000000005' and is forwarded to USER1@sip.linphone.com, the 'outgoing' is needed to specify the endpoint and codecs.

```
#### Setup this in pjsip_custom.conf:

[outgoing]
type=endpoint
disallow=all
allow=ulaw,alaw
allow=h264
from_domain=YOURDOMAIN.com
```

```
#### Setup this in extensions.conf in the [default] section

exten => 10000000005,1,NoOp() 
 same => n,Progress()
 same => n,Set(CALLERID(num)=Doorbell)
 same => n,Set(CALLERID(name)=Doorbell) 
 same => n,Dial(PJSIP/outgoing/sip:USER1@sip.linphone.org)  
 same => n,Dial(${DIALGROUP(mygroup)},40)
 same => n,Hangup()
```
 
#### Example 2: 
The problem was "no video", so i created a workaround using the "RTSP-APP". I now use the AMI (agi.php script) from Asterisk to make an originate from "RTSP-APP" to Linphone... In this example 2, the call comes in, then i send a command to AMI, to make the "RTSP-APP" call me... this provides early-video (as RTSP Stream) to Linphone... When i answer a Confbridge will be started, '10000000005' checks when the bridge is started and will join the call too.
The clue is here to use the AMI script, this is the only way an originate can work with early media, there is also an Originate app in Asterisk itself, but is has no option to  turn on early media!!

```
#### Setup this in extensions.conf in the [default] section, make sure to change the rtsp url below, and also the USER1@sip.lonphone.com. 
You see i make use of local channels 9000 and 9001 , this is to make it possible to todo a hangup (finishcall) on all incoming/outcgoing calls.

exten => 10000000005,1,NoOp()
 same => n,Progress()
 same => n,Set(CHANNEL(hangup_handler_push)=default,finishcall,1(args)) 
 same => n,Set(GLOBAL(CHANNEL-IN)=${CHANNEL})
 same => n,System(/usr/bin/php "/config/asterisk/agi.php")
 same => n,Set(i=1)
 same => n,While($[${i} < 60])
 same => n,NoOp(Confbridge number of participants : ${CONFBRIDGE_INFO(parties,1)})
 same => n,GotoIf($["${CONFBRIDGE_INFO(parties,1)}" >= "1"]?startconf) 
 same => n,Wait(1) 
 same => n,Set(i=$[${i} + 1]
 same => n,EndWhile()
 same => n(startconf),ConfBridge(1,myconferenceroom,default_user) 
 same => n,Hangup() 

exten = rtsp,1,Answer()
 same => n,RTSP-SIP(rtsp://admin:XXX@192.168.0.70:554/Streaming/Channels/102,0,asterisk,5060)
 same => n,Hangup() 
 
exten => 9000,1,NoOp()
 same => n,Progress()
 same => n,Set(CHANNEL(hangup_handler_push)=default,finishcall,1(args))  
 same => n,Set(GLOBAL(CHANNEL-9000)=${CHANNEL}) 
 same => n,Dial(Local/9001@default,,G(join_caller))
 same => n(join_caller),ConfBridge(1,myconferenceroom,marked_user) 
 same => n,ConfBridge(1,myconferenceroom,admin_user)
 same => n,Hangup()  
 
exten => 9001,1,NoOp() 
 same => n,Progress()
 same => n,Set(CHANNEL(hangup_handler_push)=default,finishcall,1(args))  
 same => n,Set(GLOBAL(CHANNEL-9001)=${CHANNEL})
 same => n,Set(__DYNAMIC_FEATURES=door)
 same => n,Set(CALLERID(num)=Doorbell)
 same => n,Set(CALLERID(name)=Doorbell)
 same => n,Set(COUNT=1)
 same => n,While($[ ${COUNT} < 60 ]) 
 same => n,Dial(PJSIP/outgoing/sip:USER1@sip.linphone.org)
 same => n,Set(HANGUPCAUSEKEYS=${HANGUPCAUSE_KEYS()})
 same => n,Set(HANGUP_CAUSE=${HANGUPCAUSE})
 same => n,Verbose(2, HANGUP_CAUSE=${HANGUPCAUSE})
 same => n,GotoIf($["${HANGUP_CAUSE}" == "21"]?exitdialplan)
 same => n,Wait(3) 
 same => n,SET(COUNT=$[${COUNT} + 1]
 same => n,EndWhile()
 same => n(exitdialplan),NoOp(Exiting dialplan: HANGUP_CAUSE=${HANGUPCAUSE}) 
 same => n,Hangup() 
 
exten => finishcall,1,NoOp() 
 same => n,System(/usr/sbin/asterisk -rx "confbridge kick 1 all")
 same => n,System(/usr/sbin/asterisk -rx "hangup request ${CHANNEL-IN}")  
 same => n,System(/usr/sbin/asterisk -rx "hangup request ${CHANNEL-9000}")
 same => n,System(/usr/sbin/asterisk -rx "hangup request ${CHANNEL-9001}")  
 same => n,Return() 
 
``` 
 
```
#### Create an agi.php in your config folder, this script is launched in the '10000000005' dialplan, make sure to change the username/secret, 
this is the AMI password thats being setup during the Asterisk Addon. The AMI script is doing the originage from  extension 'rtsp' to a 
local channel '9000', and it can be defined as early media

<?php 
$socket = fsockopen("127.0.0.1","5038", $errno, $errstr); 
fputs($socket, "Action: Login\r\n"); 
fputs($socket, "UserName: admin\r\n"); 
fputs($socket, "Secret: XXXX\r\n\r\n"); 
$wrets=fgets($socket,128); 
echo $wrets; 
fputs($socket, "Action: Originate\r\n" ); 
fputs($socket, "Channel: Local/9000@default\r\n" );
fputs($socket, "Exten: rtsp\r\n" ); 
fputs($socket, "Context: default\r\n" ); 
fputs($socket, "Priority: 1\r\n" );
fputs($socket, "Async: yes\r\n" );
fputs($socket, "EarlyMedia: true\r\n" ); 
fputs($socket, "Codecs: ulaw,h264\r\n\r\n");
$wrets=fgets($socket,128); 
?>

```

```
#### Setup this in confbrifge.conf, the  "RTSP-APP" is joining the confbridge as marked user, with video_mode=first_marked, but also as muted, to 
prevent echo, cause there is also sound coming from RTSP stream.

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
```
#### Setup this in features.conf, Here you can define dtmf buttons, like turning on a light using CURL command, or open a door. You see i use this 
feature code in local channel 9001, where i actually call the Linphone user. So when pressing 9 during the call, i can open the door.

[applicationmap]
door => 9,self,Set,CURL_RESULT=${SHELL(curl -i --digest -u admin:XXX -X PUT -d '<RemoteControlDoor><cmd>open</cmd></RemoteControlDoor>' http://192.168.0.70/ISAPI/AccessControl/RemoteControl/door/1)}

```

Like my work? You can always send me a donation: https://paypal.me/pergolafabio
