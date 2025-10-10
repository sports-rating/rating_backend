from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.sport.models import (
    Sport,
    Tournament,
    Team,
    ScoringPolicy,
    SportInstitution,
    SportInstitutionMedia,
    SportInstitutionRequest,
)
from apps.shared.utils.general import calculate_file_size


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


@admin.register(SportInstitution)
class SportInstitutionAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "director", "phone_number"]
    search_fields = ["name", "phone_number"]
    readonly_fields = ["created_time", "updated_time", "sports_list", "media_list"]

    @admin.display(description="Sports")
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

    @admin.display(description="Media")
    def media_list(self, obj):
        links = [
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:sport_sportinstitutionmedia_change", args=[media.id]),
                media.file.name,
            )
            for media in obj.media.all()
        ]
        return format_html("<br>".join(links)) if links else "-"


@admin.register(SportInstitutionMedia)
class SportInstitutionMediaAdmin(admin.ModelAdmin):
    list_display = ["id", "sport_institution_obj", "file", "media_type", "created_time"]
    search_fields = ["sport_institution__name", "media_type"]
    list_filter = ["media_type", "created_time"]
    readonly_fields = ["created_time", "sport_institution_obj", "file_size"]

    @admin.display(description="Sport Institution")
    def sport_institution_obj(self, obj):
        if obj.sport_institution:
            url = reverse("admin:sport_sportinstitution_change", args=[obj.sport_institution.id])
            return format_html('<a href="{}">{}</a>', url, obj.sport_institution.name)
        return "N/A"

    @admin.display(description="File Size")
    def file_size(self, obj):
        return calculate_file_size(obj.size)


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


@admin.register(SportInstitutionRequest)
class SportInstitutionRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "manager_full_name",
        "manager_phone_number",
        "school_name",
        "school_phone_number",
        "status",
        "created_time",
    ]
    search_fields = [
        "manager_first_name",
        "manager_last_name",
        "manager_phone_number",
        "school_name",
        "school_phone_number",
    ]
    readonly_fields = ["created_time", "manager_full_name",]

    @admin.display(description="Manager Full Name")
    def manager_full_name(self, obj: SportInstitutionRequest):
        return f"{obj.manager_first_name} {obj.manager_last_name}"
