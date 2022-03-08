FROM python:3.7-slim
RUN pip install requests
RUN apt-get update && apt-get install -y libffi-dev

COPY hik.py /hik.py
COPY hcnetsdk.py /hcnetsdk.py
COPY lib /lib

CMD [ "python3", "hik.py" ]
