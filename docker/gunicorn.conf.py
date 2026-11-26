"""gunicorn settings. supervisord starts: gunicorn -c /etc/gunicorn.conf.py config.wsgi:application

Everything that is not a command-line detail lives here, so the supervisord line stays short.
"""

import os

bind = "127.0.0.1:8000"  # only nginx talks to gunicorn
workers = int(os.environ.get("GUNICORN_WORKERS", "3"))
# The heartbeat files go to /tmp, the only writable (tmpfs) place besides the volumes (read-only root).
worker_tmp_dir = "/tmp"
# nginx is the only peer; it sets X-Real-IP after evaluating TRUSTED_PROXIES.
forwarded_allow_ips = "127.0.0.1"
accesslog = "-"
access_log_format = '%({x-real-ip}i)s %(t)s "%(r)s" %(s)s %(b)s %(L)ss'
