FROM arm32v7/python:3.9.2-buster

USER root
WORKDIR /root

RUN git clone https://github.com/iia/papycast.git
RUN pip3 install -r ./papycast/backend/requirements.txt

WORKDIR /root/papycast/backend

CMD ["python3", "backend.py"]
