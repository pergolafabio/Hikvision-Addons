FROM python:3.7-slim
RUN pip install requests
RUN apt-get update && apt-get install -y libffi-dev jq

COPY hik.py /hik.py
COPY hcnetsdk.py /hcnetsdk.py
COPY hik_unlock_door.py /hik_unlock_door.py
COPY lib /lib
COPY run.sh /run.sh 
RUN chmod +x /run.sh

CMD [ "/run.sh" ]


