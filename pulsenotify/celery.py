import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulsenotify.settings.local')

app = Celery('pulsenotify')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Celery debug task running: {self.request!r}')
