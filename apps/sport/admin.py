from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.sport.models import (
    Sport,
    Tournament,
    Result,
    Team,
    ScoringPolicy
)

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "sport", "federation"]
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


@admin.register(ScoringPolicy)
class ScoringPolicyAdmin(admin.ModelAdmin):
    list_display = ["id", "tournament_obj", "position", "score"]
    list_filter = ["tournament", "position"]
    readonly_fields = ["tournament_obj",]

    def tournament_obj(self, obj):
        if obj.tournament:
            url = reverse("admin:sport_tournament_change", args=[obj.tournament.id])
            return format_html('<a href="{}">{}</a>', url, obj.tournament.name)
        return "N/A"
