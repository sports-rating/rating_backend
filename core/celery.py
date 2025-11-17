from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from datetime import timedelta
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


app.conf.beat_schedule = {
    "store_daily_user_counts": {
        "task": "apps.user.tasks.store_daily_user_counts_task",
        "schedule": crontab(hour=1, minute=0),  # Every day at 1:00 AM
    },
    "update_media_view_counts_for_yesterday": {
        "task": "apps.user.tasks.update_media_view_counts_for_yesterday_task",
        "schedule": crontab(hour=12, minute=15),  # Every day at 12:15 PM
    }
}
app.conf.timezone = "Asia/Tashkent"
