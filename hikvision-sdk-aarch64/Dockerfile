FROM openeuler/openeuler

RUN yum -y install python-pip
RUN pip install requests

WORKDIR /app

# Hikvision SDK
COPY lib-arm_aarch64-linux /app/lib-arm_aarch64-linux

# Main application
COPY *.py /app/

ENTRYPOINT [ "python3", "/app/hik.py" ]
