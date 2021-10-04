import os

import logging
import sys

from celery import Celery

# set the default Django settings module for the 'celery' program.
from celery.signals import after_setup_logger

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'live_tracking_map.settings')

app = Celery('live_tracking_map')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@after_setup_logger.connect()
def logger_setup_handler(logger, **kwargs):
    my_handler = logging.StreamHandler(sys.stdout)
    my_handler.setLevel(logging.DEBUG)
    my_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')  # custom formatter
    my_handler.setFormatter(my_formatter)
    logger.addHandler(my_handler)

    logging.info("My log handler connected -> Global Logging")


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
