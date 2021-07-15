FROM python:3.8-slim-buster

WORKDIR /app
COPY requirements.txt /app

RUN \
  pip install -U pip --no-cache-dir && \
  pip install -r requirements.txt --no-cache-dir

COPY . /app

RUN pip install -e . --no-cache-dir

EXPOSE 8000
