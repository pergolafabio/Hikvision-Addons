# Home Assistant Add-on: Hikvision Baresip client for injecting RTSP video feed into an Asterisk conference (deprecated)
## N.B.: This addon is deprecated, a new script will be uploaded 

## Background info:

Hikvision intercom devices have the ability to register on a PBX, but the disadvantages of using the SIP setting on the device:

- When PBX is down => you miss the call :-)
- When connected to a PBX , Hikconnect cloud doesnt work anymore
- No video before pickup anymore on the indoor panels, so you dont see who is calling, quite annoying!!

There is another way!!!

In asterisk you can define an TRUNK, to register on the primary indoor station, Asterisk will act then as an indoor extension just like a real indoor device... so the call comes in, your first indoor stations starts ringing, and will forward the call to Asterisk.
For some reason the video is not forwarded... no idea why ... that's why I created this addon to have video in the call on the softphones...

Advantages:

- Hikconnect cloud, still works!
- Still video on your indoor panels!!! Most important one
- If this addon is down, the intercom still works as we register it as an extension
- You dont need access to the outdoor station, usefull for people living in appartment with no access to outdoor station.
- You dont need to use the Hikconnect app anymore, you can use your own softphone
- All local
- Verry nice intergations possible, you can even pickup/answer the call with a Lovelace SIP card!! Freaking nice! :-)  https://github.com/TECH7Fox/sip-hass-card
- Opening door also works by sending '#' during call with a softphone (enable "dtmf sip-info" on your softphone client)

## Get started

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fpergolafabio%2FHikvision-Addons)

## Installations notes:

Create a directory "baresip" in your "config" folder, copy over the files below "config" and "account" to "/config/baresip" , then start the addon, it will probably tell you that the extension 7000 is unable to register.. quite normal because you dont have a PBX yet...
https://github.com/pergolafabio/Hikvision-Addons/blob/main/hikvision-baresip/config  
https://github.com/pergolafabio/Hikvision-Addons/blob/main/hikvision-baresip/accounts

In the file "config" change line 52, thats the url for your RTSP stream...  In the file "account" change line 1, if you want to change the extension username/password...

Setup Asterisk or a PBX of your choise, i use this one: https://github.com/TECH7Fox/asterisk-hass-addons, create 2 extensions, one for this addon and one for testing. Below is an example how to create extension 7000, use the same template for your second one, use a softphone like linphone desktop for testing

```
#### Add in pjsip_custom.conf:
[7000]
type=endpoint
context=default
disallow=all
allow=ulaw,alaw
allow=h264
auth=auth7000
aors=7000
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes
direct_media=no
max_audio_streams=10
max_video_streams=10
from_domain=asterisk.com

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

Now restart this addon, make sure 7000 is now registered, and then make a video call to 7000, auto answer is enabled, so you should see the RTSP video feed!!!

## Asterisk configuration

As I told before, you can use Asterisk to register as a trunk on your primary indoor panel... 

#### Option 1 based on newer indoor panels
On same indoor panels you can already the extension with a SN.. for serial use: Q12345678, for No: 5, enter a password, the the IP is your Asterisk  instance running the addon... 
In below example, 192.168.0.71 is my primary indoor panel, 10000000005 is actually the number 5 you entered in IVMS, 192.168.0.17 is HA running Asterisk
Some indoor panels dont have the option to add extensions, then try without it, just use the trunk setup below... if you receive an 404 or 401 error when debugging sip, proceed to option 2, and skip this trunk setup... I always use the tool "sngrep", you can install it in the SSH addon with the command "apk add sngrep"


![Ivms](ivms.PNG)

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

https://gist.github.com/pergolafabio/9964ff2c2750fba447c5ca63382f4600

Try it fist from a console, to see it it works, afterwards you can use below shellcommand with an automation.


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

## Dialplan for Asterisk

#### Example 1: 
With use of regular softphones: make for example 2 extensions, on incoming call of the trunk, the group will be called with members 6000 and 6001, but no video injected with this example

```

#### Setup this in extensions.conf:

exten => 10000000005,1,NoOp() 
 same => n,Progress()
 same => n,Set(CALLERID(num)=8003)
 same => n,Set(CALLERID(name)=DS-KD8003) 
 same => n,Set(DIALGROUP(mygroup,add)=PJSIP/6000)
 same => n,Set(DIALGROUP(mygroup,add)=PJSIP/6001)  
 same => n,Dial(${DIALGROUP(mygroup)},40)
 same => n,Hangup()
 ```
 
#### Example 2: 
The problem was no video! Well, i made a workaround, the baresip client is a command line softphone...! So what i do, on an incoming call to 10000000005, i do a CURL command to the baresip client, telling to execute dialplan "7001" 
In the dialplan below you see i have created a while loop... Before the loop i do the curl command, the curl command fires the baresip softphone client to call me (dialplan 7001) ...so when i actually pickup with linhome/linphone, the conference is started... Afterwards 10000000005 will enter the conference too because the loop checks if there are members active in the conference...

I use linhome in example below, you can also use linphone, they both do early media... they also have a free flexisip server, so no need to open ports in your router to Asterisk... Another advantage, flexisip allows multiple contacts on the same account, so you have early video on all of them...! Linhome is easy to setup, everything is preconfigured, if you use linphone, make sure to enable push and early media in the settings...

```
#### Setup this in extensions.conf, make sure to add it in the [default] section!

exten => 10000000005,1,NoOp()
 same => n,Progress()
 same => n,Set(CHANNEL(hangup_handler_push)=finish_call,k,1(args))   
 same => n,Set(CURL_RESULT=${SHELL(curl http://localhost:8000/?d%207001)})  
 same => n,Set(i=1)
 same => n,While($[${i} < 40])
 same => n,NoOp(Confbridge number of participants : ${CONFBRIDGE_INFO(parties,1)})
 same => n,GotoIf($["${CONFBRIDGE_INFO(parties,1)}" >= "1"]?startconf) 
 same => n,Wait(1) 
 same => n,Set(i=$[${i} + 1]
 same => n,EndWhile()
 same => n,Hangup() 
 same => n(startconf),ConfBridge(1,myconferenceroom,default_user)  
 
exten => 7001,1,NoOp()
 same => n,Set(GLOBAL(CHANNEL7001)=${CHANNEL}) 
 same => n,Dial(Local/7002@default,,G(join_caller))
 same => n(join_caller),ConfBridge(1,myconferenceroom,marked_user)
 same => n(join_callee),ConfBridge(1,myconferenceroom,admin_user) 
 
exten => 7002,1,NoOp() 
 same => n,Set(CHANNEL(hangup_handler_push)=finish_call,k,1(args))
 same => n,Set(GLOBAL(CHANNEL7002)=${CHANNEL}) 
 same => n,Set(CALLERID(num)=8003)
 same => n,Set(CALLERID(name)=DS-KD8003) 
 same => n,Set(COUNT=1)
 same => n,While($[ ${COUNT} < 60 ])
 same => n,Dial(PJSIP/outgoing/sip:USER1@sip.linhome.org)  
 same => n,Set(HANGUPCAUSEKEYS=${HANGUPCAUSE_KEYS()})
 same => n,Set(HANGUP_CAUSE=${HANGUPCAUSE})
 same => n,Verbose(2, HANGUP_CAUSE=${HANGUPCAUSE})
 same => n,GotoIf($["${HANGUP_CAUSE}" == "21"]?exitdialplan)
 same => n,Wait(5) 
 same => n,SET(COUNT=$[${COUNT} + 1]
 same => n,EndWhile()
 same => n(exitdialplan),NoOp(Exiting dialplan: HANGUP_CAUSE=${HANGUPCAUSE}) 
 same => n,Hangup()
 
[finish_call]
exten => k,1,NoOp()
 same => n,System(/usr/sbin/asterisk -rx "confbridge kick 1 all")
 same => n,System(/usr/sbin/asterisk -rx "hangup request ${CHANNEL7001}")  
 same => n,System(/usr/sbin/asterisk -rx "hangup request ${CHANNEL7002}") 
 same => n,Return()  
 
``` 

```
#### Setup this in pjsip_custom.conf:

# Used for outgoing calling to linphone/linhome services
[outgoing]
type=endpoint
disallow=all
allow=ulaw,alaw
allow=h264
from_domain=asterisk.com
```
 
```
#### Setup this in confbrifge.conf:
# Extension 7000 (RTSP extension) is the marked user, i have video_mode enabed to the first marked user, and i muted that extension


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

## NOTES: Multiple doorbells? Multiple cameras?
In the 10000000005 dialplan i send a command to the baresip console client to call 70001. In the config file as described above, the rtsp stream configured... But if you want tos etup multiple trunks, for multiple doorbells, and you have another incoming call, we need to change the rtsp source... The httpd module has an optio to send /vidsrc... So in 10000000005 dialplan, right before the curl to 7001, add another curl to change source

This needs to be sended:

```
/vidsrc avformat,rtsp://admin:XXX@192.168.0.70:554/Streaming/Channels/101
```

But it needs to be encoded, use this link for it: https://www.url-encode-decode.com/ 

So the curl becomes:
```
curl http://localhost:8000/?%2Fvidsrc%20avformat%2Crtsp%3A%2F%2Fadmin%3AXXX%40192.168.0.70%3A554%2FStreaming%2FChannels%2F101
```



Like my work? You can always send me a donation: https://paypal.me/pergolafabio
