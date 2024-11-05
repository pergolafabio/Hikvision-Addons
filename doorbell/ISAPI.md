# Home Assistant Add-on: Hikvision Doorbell

## Usefull ISAPI commands

- GET /ISAPI/VideoIntercom/callStatus?format=json
- PUT /ISAPI/AccessControl/RemoteControl/door/1 <RemoteControlDoor><cmd>open</cmd></RemoteControlDoor>
- PUT /ISAPI/System/reboot
- PUT /ISAPI/VideoIntercom/callSignal?format=json {"CallSignal":{"cmdType":"reject"}}
- GET /ISAPI/VideoIntercom/keyCfg/1
- PUT /ISAPI/VideoIntercom/keyCfg/1 <KeyCfg><id>1</id><module>main</module><callNumber>1</callNumber><enableCallCenter>false</enableCallCenter><templateNo>1</templateNo></KeyCfg>
- POST /ISAPI/SecurityCP/status/outputStatus?format=json {"OutputCond":{"maxResults":2,"outputModuleNo":0,"searchID":"1","searchResultPosition":0}}
- POST /ISAPI/AccessControl/UserInfo/Search?format=json {"UserInfoSearchCond":{"searchID":"1","searchResultPosition": 0,"maxResults": 10,"EmployeeNoList":[{"employeeNo":"6"}]}}
- POST /ISAPI/AccessControl/CardInfo/Search?format=json {"CardInfoSearchCond": {"searchID": "1","maxResults": 10,"searchResultPosition": 0,"EmployeeNoList": [{ "employeeNo": "6" }]}}

And a lot more can be found on the SDK documentation online

