FROM python:3.9

USER root
WORKDIR /root

RUN git clone https://github.com/iia/papycast.git
RUN pip3 install -r ./papycast/backend/requirements.txt

ENV FLASK_APP="backend:app"
ENV FLASK_ENV="production"

WORKDIR /root/papycast/backend

CMD flask run --no-reload --host=0.0.0.0
