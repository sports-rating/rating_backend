from django.contrib import admin


from apps.education.models import (
    Education,
    School
)

@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ["id", "sport", "start_year", "end_year"]


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "director", "phone_number"]
    search_fields = ["name", ]
