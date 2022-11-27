FROM archlinux
#FROM yantis/archlinux-tiny
USER root
COPY run.sh /run.sh
RUN pacman -Sy
RUN pacman -S ffmpeg baresip libtg_owt --noconfirm
CMD ["/bin/bash", "/run.sh"]

########################### Below based op Debian

# RUN apt-get update && apt-get install -y ffmpeg openssl build-essential git libssl-dev libavformat-dev libavdevice-dev  vpx-tools libvpx-dev pkg-config cmake
# USER root

#WORKDIR /
#RUN git clone https://github.com/baresip/re
#WORKDIR /re
#RUN make && make install

#WORKDIR /
#RUN git clone https://github.com/baresip/rem
#WORKDIR /rem
#RUN make && make install

#WORKDIR /
#RUN git clone https://github.com/baresip/baresip-apps.git

#WORKDIR /
#RUN git clone https://github.com/baresip/baresip
#WORKDIR /baresip

# RUN cmake -B build -DAPP_MODULES_DIR=../baresip-apps/modules -DAPP_MODULES="b2bua"
# RUN cmake --build build -j

#WORKDIR /
#RUN /baresip/build/baresip
