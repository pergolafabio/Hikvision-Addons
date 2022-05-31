FROM debian:bullseye

USER root
WORKDIR /app

COPY run.sh /app/run.sh
COPY linphonerc /app/linphonerc
COPY v4l2loopback-5.15.41.ko /app/v4l2loopback.ko
RUN mkdir -p /root/.local/share/linphone
# RUN mkdir -p /usr/lib/x86_64-linux-gnu/mediastreamer/plugins
# COPY libmsopenh264.a /usr/lib/x86_64-linux-gnu/mediastreamer/plugins/libmsopenh264.a
# COPY libmsopenh264.so /usr/lib/x86_64-linux-gnu/mediastreamer/plugins/libmsopenh264.so

RUN apt-get update \
    && apt-get install -y git nano ffmpeg libavcodec-dev libswscale-dev libavutil-dev libx264-dev liblinphone-dev jq sed kmod linphone-nogtk


## Changing versmagic!
# RUN git clone https://github.com/yaxinsn/vermagic
# RUN /app/vermagic/vermagic -v "5.15.41 SMP mod_unload " /app/v4l2loopback.ko

## Creating H264 plugins!
RUN apt-get install -y build-essential cmake pkg-config nasm yasm libtool
RUN git clone https://github.com/cisco/openh264.git
WORKDIR /app/openh264
RUN make ARCH=x86_64
RUN make install
WORKDIR /app
RUN git clone https://gitlab.linphone.org/BC/public/msopenh264.git
WORKDIR /app/msopenh264 
RUN cmake . -DCMAKE_PREFIX_PATH=/usr/local/lib/pkgconfig 
RUN make 
RUN make install
## Plugin files created in dir below, but needed in plugin dir
RUN mkdir -p /usr/lib/x86_64-linux-gnu/mediastreamer/plugins
RUN cp /usr/local/lib/x86_64-linux-gnu/mediastreamer/plugins/libmsopenh264.a /usr/lib/x86_64-linux-gnu/mediastreamer/plugins
RUN cp /usr/local/lib/x86_64-linux-gnu/mediastreamer/plugins/libmsopenh264.so /usr/lib/x86_64-linux-gnu/mediastreamer/plugins

## Command to copy files outside container for testing
# docker cp addon_aff2db71_hikvision_v4l2loopback:/usr/local/lib/x86_64-linux-gnu/mediastreamer/plugins/libmsopenh264.a /addons
# docker cp addon_aff2db71_hikvision_v4l2loopback:/usr/local/lib/x86_64-linux-gnu/mediastreamer/plugins/libmsopenh264.so /addons

CMD ["/bin/bash", "/app/run.sh"]
#ENTRYPOINT ["tail", "-f", "/dev/null"]

