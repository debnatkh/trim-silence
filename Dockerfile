FROM python:3.8

COPY . /opt/app
WORKDIR /opt/app

RUN pip install -r requirements.txt

ENTRYPOINT /bin/bash
