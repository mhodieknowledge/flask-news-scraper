# gunicorn.conf.py
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
worker_class = 'sync'
timeout = 120  # 2 minutes timeout for long scraping tasks
keepalive = 5
bind = "0.0.0.0:10000"  # Render uses port 10000 internally
