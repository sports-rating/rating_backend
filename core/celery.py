from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from datetime import timedelta

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("rating_backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# app.conf.beat_schedule = {
#     "update_tree_oxygen_production": {
#         "task": "apps.tree.tasks.update_tree_oxygen_production",
#         "schedule": timedelta(seconds=15),  # every 5 minutes # for testing 15s
#     }
# }
app.conf["timezone"] = "UTC"
