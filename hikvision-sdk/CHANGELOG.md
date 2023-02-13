# Changelog
## 2.2

- Updated SDK for amd64 to: HCNetSDKV6.1.9.4_build20220412_linux64, also changed docker image to ubuntu for this

## 2.1

- Added reboot command as stdin service to restart the outdoor station (some models freeze with use of hikconnect, so you can now automate a restart at night)
- Added more logging

## 2.0

- Multi-architecture build! 
- Improve logging

## 1.6

- Downgraded python version to 3.10.8, newer python version gave "segmentation fault", addon instantly stops

## 1.5

- Added Callsignal command with stdin service, to abort/reject calls
