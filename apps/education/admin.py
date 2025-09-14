from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

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
    search_fields = ["name", "phone_number"]
    readonly_fields = ["created_time", "updated_time", "sports_list"]

    def sports_list(self, obj):
        links = [
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:sport_sport_change", args=[sport.id]),
                sport.name,
            )
            for sport in obj.sports.all()
        ]
        return format_html("<br>".join(links)) if links else "-"
