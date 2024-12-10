#!/bin/bash

./manage.py collectstatic --no-input
./manage.py wait_for_db
./manage.py migrate --no-input
gunicorn -c deployment/gunicorn_conf.py core.wsgi