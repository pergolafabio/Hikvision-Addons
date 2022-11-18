FROM openeuler/openeuler

RUN yum -y install python-pip
RUN pip install requests

COPY hik.py /hik.py
COPY hcnetsdk.py /hcnetsdk.py
COPY lib-arm_aarch64-linux /lib-arm_aarch64-linux

CMD [ "python3", "hik.py" ]
