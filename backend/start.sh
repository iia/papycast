#!/bin/bash

source /home/pi/git/iia/papycast/backend/venv/bin/activate

export FLASK_APP="backend:app"
export FLASK_ENV=production

#
# NOTE:
#    Reload option breaks threading and signal
#    handling by initialising backend.py twice
#    while forking.
#
flask run --no-reload --host=0.0.0.0
