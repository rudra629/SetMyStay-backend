# Gunicorn settings (picked up automatically by `gunicorn setmystay_backend.wsgi:application`).
# Before this file the server used 1 worker that answered one request at a time.
import os

# Processes x threads = requests handled at the same time (2 x 4 = 8 by default).
# On a bigger Render plan raise GUNICORN_WORKERS (about 2 per CPU) in the environment settings.
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
worker_class = "gthread"
timeout = 60            # uploads of photos/videos can take a while
graceful_timeout = 30
keepalive = 5
# Restart workers now and then so memory stays low on small plans
max_requests = 1000
max_requests_jitter = 100
