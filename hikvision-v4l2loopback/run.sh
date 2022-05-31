#!/bin/bash

#Changing options variables
CONFIG_PATH=/data/options.json

REG_PROXY="$(jq --raw-output '.reg_proxy' $CONFIG_PATH)"
REG_IDENTITY="$(jq --raw-output '.reg_identity' $CONFIG_PATH)"
USERNAME="$(jq --raw-output '.username' $CONFIG_PATH)"
PASSWD="$(jq --raw-output '.passwd' $CONFIG_PATH)"
DOMAIN="$(jq --raw-output '.domain' $CONFIG_PATH)"
RTSP="$(jq --raw-output '.rtsp' $CONFIG_PATH)"

sed -i "s/reg_proxy=sip:192.168.0.17:5050*/reg_proxy=${REG_PROXY}/g" /app/linphonerc
sed -i "s/reg_identity=sip:1234@192.168.0.17:5050*/reg_identity=${REG_IDENTITY}/g" /app/linphonerc
sed -i "s/username=1234*/username=${USERNAME}/g" /app/linphonerc
sed -i "s/passwd=4321*/passwd=${PASSWD}/g" /app/linphonerc
sed -i "s/domain=192.168.0.17*/domain=${DOMAIN}/g" /app/linphonerc

echo -e "Trying to load the v4l2loopback kernel module..."
insmod /app/v4l2loopback.ko exclusive_caps=1 devices=1
echo -e "Check if v4l2loopback modulde is loaded..."
lsmod
sleep 1
echo -e "Injecting RTSP stream into /dev/video0..."
${RTSP}
echo -e "Waiting 8 seconds before starting linphone (/dev/video0 must be processed first)..."
sleep 8
echo -e "Starting linphone..."
linphonec -a -C -c /app/linphonerc

# Usefull Linphonec commands: webcam list // webcam use 0  // proxy add / autoanswer enable
