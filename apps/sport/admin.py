from django.contrib import admin

from apps.sport.models import (
    Sport,
    Tournament,
    Result,
    Team,
    Federation,
    AgeGroup
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


@admin.register(Federation)
class FederationAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "region", "is_national"]
    search_fields = ["name", "region__name"]
    list_filter = ["is_national", "region"]
    readonly_fields = ["created_time", "age_groups", "documents"]

    def age_groups(self, obj):
        """Display the age groups associated with this federation"""
        return ", ".join([age_group.name for age_group in obj.age_groups.filter(federation=obj)])

    age_groups.short_description = "Age Groups"

    def users(self, obj):
        """Display users associated with this federation"""
        return ", ".join([user.username for user in obj.users.all()])

    users.short_description = "Users"

    def documents(self, obj):
        """Display documents associated with this federation"""
        return ", ".join([doc.name for doc in obj.documents.all()]) if obj.documents.exists() else "-"


@admin.register(AgeGroup)
class AgeGroupAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "sport", "age"]
    search_fields = ["name", "sport__name"]
    list_filter = ["sport"]
