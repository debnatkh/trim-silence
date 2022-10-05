FROM python:3.8

COPY . /opt/app
WORKDIR /opt/app

RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y ffmpeg

ENTRYPOINT /bin/bash
