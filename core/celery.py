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

# app.conf.beat_schedule = {
#     "update_tree_oxygen_production": {
#         "task": "apps.tree.tasks.update_tree_oxygen_production",
#         "schedule": timedelta(seconds=15),  # every 5 minutes # for testing 15s
#     }
# }
app.conf.beat_schedule = {
    "store_daily_user_counts": {
        "task": "apps.user.tasks.store_daily_user_counts_task",
        "schedule": crontab(hour=1, minute=0),  # Every day at 1:00 AM
    },
    "update_media_counts_for_yesterday": {
        "task": "apps.user.tasks.update_media_counts_for_yesterday_task",
        "schedule": crontab(hour=12, minute=5),  # Every day at 12:05 PM
    }
}
app.conf.timezone = "Asia/Tashkent"
