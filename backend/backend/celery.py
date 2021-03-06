from __future__ import absolute_import
from celery import Celery
import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')


app = Celery('backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# debug 실행내용의 출력
@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

