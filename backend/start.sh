#!/bin/sh

export FLASK_APP="backend:app"
export FLASK_ENV=production

#
# NOTE:
#    Reload option breaks threading and signal
#    handling by initialising backend.py twice
#    while forking.
#
flask run --no-reload --host=0.0.0.0
