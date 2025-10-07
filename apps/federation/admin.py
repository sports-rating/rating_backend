from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.federation.models import (
    AgeGroup,
    Federation,
    FederationAgeGroup
)


@admin.register(Federation)
class FederationAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "region", "is_national"]
    search_fields = ["name", "region__name"]
    list_filter = ["is_national", "region"]
    readonly_fields = ["created_time", "age_groups", "documents", "user_objs"]

    @admin.display(description="Age Groups")
    def age_groups(self, obj: Federation) -> str:
        """Display the age groups associated with this federation"""
        links = [
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:federation_federationagegroup_change", args=[age_group.id]),
                str(age_group.age_group.name)
            )
            for age_group in obj.age_group_links.all()
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


@admin.register(FederationAgeGroup)
class FederationAgeGroupAdmin(admin.ModelAdmin):
    list_display = ["id", "federation", "age_group"]
    search_fields = ["federation__name", "age_group__name"]
    list_filter = ["federation", "age_group"]
    readonly_fields = ["age_group_obj", "age_group_weights"]

    @admin.display(description="Age Group")
    def age_group_obj(self, obj: FederationAgeGroup) -> str:
        return format_html(
            '<a href="{}">Age Group</a>',
            reverse("admin:federation_agegroup_change", args=[obj.age_group.id]),
        )

    @admin.display(description="Age Group Weights")
    def age_group_weights(self, obj: FederationAgeGroup) -> str:
        """Display weights associated with this age group"""
        return "\n".join([str(weight) for weight in obj.age_group.weights]) if obj.age_group.weights else "-"


@admin.register(AgeGroup)
class AgeGroupAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "sport", "min_age", "max_age"]
    search_fields = ["name", "sport__name"]
    list_filter = ["sport"]
