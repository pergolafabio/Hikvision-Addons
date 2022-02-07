#!/bin/sh

CONFIG_PATH=/data/options.json

IP="$(jq --raw-output '.ip' $CONFIG_PATH)"
USERNAME="$(jq --raw-output '.username' $CONFIG_PATH)"
PASSWORD="$(jq --raw-output '.password' $CONFIG_PATH)"
BEARER="$(jq --raw-output '.bearer' $CONFIG_PATH)"
URL_STATES="$(jq --raw-output '.url_states' $CONFIG_PATH)"
SENSOR_DOOR="$(jq --raw-output '.sensor_door' $CONFIG_PATH)"
SENSOR_CALLSTATUS="$(jq --raw-output '.sensor_callstatus' $CONFIG_PATH)"

python3 hik.py $IP $USERNAME $PASSWORD $BEARER $URL_STATES $SENSOR_DOOR $SENSOR_CALLSTATUS
#python3 hik.py 192.168.0.70 admin Password01 eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJkYzZjM2ZmNDMyMjc0MGNiYWVmMjcxODUxYzY3NmE1MSIsImlhdCI6MTU0Mzk1NTcyNiwiZXhwIjoxODU5MzE1NzI2fQ.OGMzdM0eBte89-viStAsTjHQw8icHUDNxTtOuyzltNA http://localhost:8123/api/states/ hikvision_door hikvision_callstatus

