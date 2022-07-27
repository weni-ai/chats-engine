#!/bin/bash

echo "Running collectstatic"
python manage.py collectstatic --noinput

ls

echo "Starting server"
gunicorn chats.asgi -c gunicorn.conf.py