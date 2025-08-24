from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

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
    readonly_fields = ["created_time", "age_groups", "documents", "user_objs"]

    @admin.display(description="Age Groups")
    def age_groups(self, obj: Federation) -> str:
        """Display the age groups associated with this federation"""
        age_groups = AgeGroup.objects.filter(federation_links__federation=obj)
        links = [
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:federation_agegroup_change", args=[age_group.id]),
                str(age_group.name)
            )
            for age_group in age_groups.all()
        ]
        return format_html("<br>".join(links)) if links else "-"

    @admin.display(description="User objs")
    def user_objs(self, obj: Federation) -> str:
        """Display users associated with this federation"""
        links = [
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:user_user_change", args=[user.id]),
                str(user.full_name)
            )
            for user in obj.users.all()
        ]
        return format_html("<br>".join(links)) if links else "-"

    @admin.display(description="Documents")
    def documents(self, obj: Federation) -> str:
        """Display documents associated with this federation"""
        return ", ".join([str(doc.id) for doc in obj.documents.all()]) if obj.documents.exists() else "-"


@admin.register(AgeGroup)
class AgeGroupAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "sport", "age"]
    search_fields = ["name", "sport__name"]
    list_filter = ["sport"]
