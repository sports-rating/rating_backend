#!/bin/bash

./manage.py collectstatic --no-input # means take yes in input by default
./manage.py wait_for_db
./manage.py migrate --no-input
./manage.py compilemessage
gunicorn -c deployment/gunicorn_conf.py core.wsgi