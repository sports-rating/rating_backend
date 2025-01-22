from django.contrib import admin

from dashboard.models import (
    Tournament,
    Sport,
    Team,
    PrivacyPolicy,
    TermsOfCondition
)

from user.models import (
    School
)

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "start_time", "end_time", "sport"]
    search_fields = ["name", "sport__name"]
    list_filter = ["sport",]


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ["id", "name",]
    search_fields = ["name",]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "founded_year", "sport"]
    search_fields = ["name",]


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "director", "phone_number"]
    search_fields = ["name", ]


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "language"]
    search_fields = ["title",]
    fields = ["language", "title", "text"]


@admin.register(TermsOfCondition)
class TermsOfConditionAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "language"]
    search_fields = ["title",]
    fields = ["language", "title", "text"]
