from django.contrib import admin

from apps.sport.models import (
    Sport,
    Tournament,
    Result,
    Team,
)

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "sport"]
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


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "sport", "founded_year"]
    search_fields = ["name",]
