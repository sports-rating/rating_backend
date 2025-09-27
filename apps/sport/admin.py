from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.sport.models import (
    Sport,
    Tournament,
    Result,
    Team,
    ScoringPolicy,
    School
)


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "sport", "federation"]
    search_fields = ["name", "sport__name"]
    list_filter = ["sport",]
    readonly_fields = ["federation_obj", "scoring_policies",]

    @admin.display(description="Federation")
    def federation_obj(self, obj):
        if obj.federation:
            url = reverse("admin:federation_federation_change", args=[obj.federation.id])
            return format_html('<a href="{}">{}</a>', url, obj.federation.name)
        return "N/A"

    @admin.display(description="Scoring Policies")
    def scoring_policies(self, obj):
        policies = ScoringPolicy.objects.filter(tournament=obj)
        if policies.exists():
            links = []
            for policy in policies:
                url = reverse("admin:sport_scoringpolicy_change", args=[policy.id])
                links.append(format_html('<a href="{}">Position: {} - Score: {}</a>', url, policy.position, policy.score))
            return format_html("<br>".join(links))
        return "No scoring policies defined."


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ["id", "name",]
    search_fields = ["name",]


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


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ["id", "tournament", "year", "currently_participating"]
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
            name = f"{obj.tournament.name} - ({obj.tournament.sport.name})"
            return format_html('<a href="{}">{}</a>', url, name)
        return "N/A"
