FROM python:3.9.2

USER root
WORKDIR /root

COPY ./backend/ ./backend/
RUN pip3 install -r ./backend/requirements.txt

WORKDIR /root/backend

CMD ["python3", "backend.py"]
