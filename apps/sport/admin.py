from django.contrib import admin

from .models import (
    Sport,
    Tournament,
    Result
)


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "start_time", "sport"]
    search_fields = ["name", "sport__name"]
    list_filter = ["sport",]


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ["id", "name",]
    search_fields = ["name",]


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ["id", "country", "tournament", "year", "currently_participating"]
    list_filter = ["currently_participating",]
