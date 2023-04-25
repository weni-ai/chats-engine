#!/bin/bash

echo "Running collectstatic"
python manage.py collectstatic --noinput

echo "Starting server"
exec gunicorn chats.asgi -c gunicorn.conf.py
