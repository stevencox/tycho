FROM python:3.7.3-alpine

WORKDIR /

RUN apk -U add build-base libffi-dev libressl-dev
RUN apk add libffi-dev
RUN pip install --upgrade pip
COPY requirements.txt ./
RUN pip install --no-cache-dir -r ./requirements.txt

RUN apk add git
RUN git clone https://github.com/heliumplusdatastage/tycho.git
COPY . /tycho

ENV PYTHONPATH /tycho
ENV WORKERS=2
ENV APP_MODULE=tycho.api:app
ENV APP_NAME=tycho
ENV PORT=8099

ENV TYCHO=https://tycho.renci.org

ENTRYPOINT /usr/local/bin/gunicorn --workers=$WORKERS --bind=0.0.0.0:$PORT --name=$APP_NAME --timeout=600 $APP_MODULE
