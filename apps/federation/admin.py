from django.contrib import admin

from apps.federation.models import (
    AgeGroup,
    Federation,
    FederationAgeGroup,
    FederationDocument
)

# Register your models here.
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
