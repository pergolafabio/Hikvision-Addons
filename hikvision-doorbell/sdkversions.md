Aarch64 : HCNetSDKV6.1.8.101_build20211210_Arm_aarch64-linux

Amd64 : HCNetSDKV6.1.6.3_build20200925_Linux64

To run on Alpine : patchelf --set-rpath '$ORIGIN' libssl.so
See: https://github.com/pergolafabio/Hikvision-Addons/issues/354