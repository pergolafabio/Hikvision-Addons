# Home Assistant Add-on: Hikvision Doorbell

## Usefull ISAPI commands

```
- GET /ISAPI/VideoIntercom/callStatus?format=json
- PUT /ISAPI/AccessControl/RemoteControl/door/1 <RemoteControlDoor><cmd>open</cmd></RemoteControlDoor>
- PUT /ISAPI/System/reboot
- PUT /ISAPI/VideoIntercom/callSignal?format=json {"CallSignal":{"cmdType":"reject"}}
- GET /ISAPI/VideoIntercom/keyCfg/1
- PUT /ISAPI/VideoIntercom/keyCfg/1 <KeyCfg><id>1</id><module>main</module><callNumber>1</callNumber><enableCallCenter>false</enableCallCenter><templateNo>1</templateNo></KeyCfg>
- PUT /ISAPI/SecurityCP/control/outputs/0?format=json {"OutputsCtrl":{"switch":"open"}}
- POST /ISAPI/SecurityCP/status/outputStatus?format=json {"OutputCond":{"maxResults":2,"outputModuleNo":0,"searchID":"1","searchResultPosition":0}}
- POST /ISAPI/AccessControl/UserInfo/Search?format=json {"UserInfoSearchCond":{"searchID":"1","searchResultPosition": 0,"maxResults": 10,"EmployeeNoList":[{"employeeNo":"6"}]}}
- POST /ISAPI/AccessControl/CardInfo/Search?format=json {"CardInfoSearchCond": {"searchID": "1","maxResults": 10,"searchResultPosition": 0,"EmployeeNoList": [{ "employeeNo": "6" }]}}
- GET /ISAPI/System/Audio/AudioOut/channels/1
- PUT /ISAPI/System/Audio/AudioOut/channels/1<AudioOut><id>1</id><AudioOutVolumelist><AudioOutVlome><type>audioOutput</type><volume>0</volume><talkVolume>7</talkVolume></AudioOutVlome></AudioOutVolumelist></AudioOut>
- GET /ISAPI/System/IO/capabilities
- GET /ISAPI/System/IO/outputs/1
- PUT /ISAPI/System/IO/outputs/<ID>/trigger <IOPortData><outputState>high</outputState></IOPortData>
- PUT /ISAPI/System/IO/outputs/<ID>/trigger <IOPortData><outputState>low</outputState></IOPortData>
- GET /ISAPI/VideoIntercom/SubModuleBacklight?format=json
- PUT /ISAPI/VideoIntercom/SubModuleBacklight?format=json {"backlightMode":"auto","customBacklightTime":{},"hostSyncEnabled":true}
- PUT /ISAPI/VideoIntercom/SubModuleBacklight?format=json {"backlightMode":"custom","customBacklightTime":{"beginTime":"21:00:00","endTime":"07:00:00"},"hostSyncEnabled":true}
```

And a lot more can be found on the SDK documentation online

