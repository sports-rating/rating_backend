from django.contrib import admin

from dashboard.models import (
    Tournament,
)

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "start_time", "end_time", "sport_type"]
    list_filter = ["sport_type",]