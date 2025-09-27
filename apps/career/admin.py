from django.contrib import admin


# Register your models here.
from apps.career.models import (
    Education
)


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ["id", "sport", "start_year", "end_year"]
