from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.education.models import (
    Education
)


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ["id", "sport", "start_year", "end_year"]
