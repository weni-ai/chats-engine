import multiprocessing
import os

workers = os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1)
proc_name = "chats"
default_proc_name = proc_name
# worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "gunicorn.access"
timeout = 120
bind = "0.0.0.0"
raw_env = ["DJANGO_SETTINGS_MODULE=chats.settings"]
