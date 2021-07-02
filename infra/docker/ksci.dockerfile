FROM python:3.9-slim

ENV FLASK_APP=ksci/api.py
WORKDIR /app
RUN apt update && apt-get install -y git
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY ksci/ ./ksci/
