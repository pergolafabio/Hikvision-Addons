ARG BUILD_FROM
FROM $BUILD_FROM

USER root

COPY run.sh /run.sh
RUN apk update \
    && apk add git nano make gcc iproute2 wget alpine-sdk linux-headers

WORKDIR /
RUN wget http://ftp.gnu.org/gnu/osip/libosip2-4.1.0.tar.gz
RUN tar xf libosip2-4.1.0.tar.gz
WORKDIR /libosip2-4.1.0
RUN ./configure && make && make install

WORKDIR /
RUN wget http://download.savannah.gnu.org/releases/exosip/libeXosip2-4.1.0.tar.gz
RUN tar xf libeXosip2-4.1.0.tar.gz
WORKDIR /libeXosip2-4.1.0
RUN ./configure && make && make install

WORKDIR /
## Creating H264 encoder plugin!
RUN git clone https://github.com/larkguo/sip2rtsp.git
WORKDIR /sip2rtsp
RUN ./configure && make && make install

WORKDIR /
CMD ["/bin/bash", "/run.sh"]
#ENTRYPOINT ["tail", "-f", "/dev/null"]

