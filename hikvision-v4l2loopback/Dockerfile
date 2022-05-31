#ARG BUILD_FROM
#FROM $BUILD_FROM
FROM debian:bullseye

USER root
WORKDIR /app

COPY run.sh /app/run.sh
COPY linphonerc /app/linphonerc
COPY v4l2loopback-5.15.41.ko /app/v4l2loopback.ko
RUN mkdir -p /root/.local/share/linphone

# RUN echo -e "https://dl-cdn.alpinelinux.org/alpine/edge/community\nhttps://dl-cdn.alpinelinux.org/alpine/edge/main\nhttps://dl-cdn.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories
# RUN apk add --no-cache git nano linphone ffmpeg jq sed
RUN apt-get update \
    && apt-get install -y git nano linphone-nogtk ffmpeg libavcodec-dev libswscale-dev libavutil-dev jq sed kmod

# RUN git clone https://github.com/yaxinsn/vermagic
# RUN /app/vermagic/vermagic -v "5.15.41 SMP mod_unload " /app/v4l2loopback.ko

CMD ["/bin/bash", "/app/run.sh"]
#ENTRYPOINT ["tail", "-f", "/dev/null"]



