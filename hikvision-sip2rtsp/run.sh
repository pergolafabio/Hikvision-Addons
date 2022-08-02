#!/bin/bash
cp /config/sip2rtsp.cfg /sip2rtsp.cfg
export LD_LIBRARY_PATH=/lib:/usr/lib:/usr/local/lib
echo -e "Starting sip2rtsp..."
sip2rtsp -f /sip2rtsp.cfg


