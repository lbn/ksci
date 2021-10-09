FROM python:3.9-slim

ENV FLASK_APP=kscipy/api.py
WORKDIR /app
RUN apt update && apt-get install -y git
COPY ./requirements.txt /app
RUN pip install -r requirements.txt
COPY . /app/kscipy
