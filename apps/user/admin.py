from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    User, 
    Sportsman, 
    Trainer,
    UserMedia,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "username",
        "phone_number",
        "user_role",
        "gender",
        "is_verified",
        "created_time",
    ]
    search_fields = ["username", "phone_number"]
    list_filter = ["is_verified",]
    readonly_fields = ["created_time", "educations", "results", "profile"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "first_name",
                    "middle_name",
                    "last_name",
                    "gender",
                    "pinfl",
                    "phone_number",
                    "is_verified",
                    "user_role",
                    "educations",
                    "results",
                    "profile",
                )
            },
        ),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "user_permissions")}),
    )
    filter_horizontal = ("user_permissions",)

    def educations(self, obj):
        """Display educations as clickable links."""
        links = [
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:education_education_change", args=[edu.id]),
                str(edu),
            )
            for edu in obj.educations.all()
        ]
        return format_html("<br>".join(links)) if links else "-"

    def results(self, obj):
        """Display results as clickable links."""
        links = [
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:sport_result_change", args=[res.id]),
                str(res),
            )
            for res in obj.results.all()
        ]
        return format_html("<br>".join(links)) if links else "-"

    def profile(self, obj):
        """Display trainer or sportsman profile as a clickable link."""
        if obj.user_role == "trainer" and hasattr(obj, "trainer_profile"):
            return format_html(
                '<a href="{}">Trainer Profile</a>',
                reverse("admin:user_trainer_change", args=[obj.id]),
            )
        elif obj.user_role == "sportsman" and hasattr(obj, "sportsman_profile"):
            return format_html(
                '<a href="{}">Sportsman Profile</a>',
                reverse("admin:user_sportsman_change", args=[obj.id]),
            )
        return "-"

    educations.short_description = "Educations"
    results.short_description = "Results"
    profile.short_description = "Profile"


@admin.register(Sportsman)
class SportsmanAdmin(admin.ModelAdmin):
    list_display = ["user_id", "user", "sport", "created_time"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "sport",
                    "trainer",
                    "skill_level",
                    "division",
                    "bio",
                )
            },
        ),
        ("User Metrics", {"fields": ("user_metrics", )}),
        ("Adress", {"fields": ("address",)}),
        ("Social media", {"fields": ("social_media",)}),
        # ("Media", {"fields": ("media",)}),
        
    )
    list_filter = ["skill_level",]


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ["user_id", "user", "sport", "created_time"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "sport",
                    "skill_level",
                    "division",
                    "bio",
                )
            },
        ),
        ("User Metrics", {"fields": ("user_metrics", )}),
        ("Adress", {"fields": ("address",)}),
        ("Social media", {"fields": ("social_media",)}),
        # ("Media", {"fields": ("media",)}),
        
    )
    list_filter = ["skill_level",]


@admin.register(UserMedia)
class UserMediaAdmin(admin.ModelAdmin):
    list_display = ["id", "media_type", "size", "extension"]
    list_filter = ["media_type", "extension"]
