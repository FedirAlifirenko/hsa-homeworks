FROM python:3.8-slim-buster

WORKDIR /app
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .

ENTRYPOINT ["uvicorn", "webapp:app", "--host", "0.0.0.0"]
