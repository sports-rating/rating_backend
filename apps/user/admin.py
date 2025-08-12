from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.user.models import (
    User, 
    Sportsman, 
    Trainer,
    UserMedia,
    ArchivedTrainer,
    UserRequest,
    UserNotification
)
from apps.shared.models import (
    Country,
    Region,
    District,
    Neighborhood
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "first_name",
        "last_name",
        "phone_number",
        "user_role",
        "gender",
        "is_verified",
        "created_time",
    ]
    search_fields = ["username", "phone_number"]
    list_filter = ["is_verified",]
    readonly_fields = ["created_time", "educations", "results", "profile"]
    list_filter = ["user_role", "gender", "region", "district"]
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
                    "region",
                    "district",
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


@admin.register(ArchivedTrainer)
class ArchivedTrainerAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]


@admin.register(UserRequest)
class UserRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "sender_obj", "receiver_obj", "request_type", "status"]
    search_fields = ['sender__first_name', 'sender__last_name', 'receiver__first_name', 'receiver__last_name']
    list_per_page = 10
    odering = ['-created_time']
    readonly_fields = ["sender_obj", "receiver_obj"]

    def sender_obj(self, obj):
        if obj.sender:
            url = reverse("admin:user_user_change", args=[obj.sender.id])
            return format_html('<a href="{}">{}</a>', url, obj.sender.username)
        return "N/A"
    sender_obj.short_description = "Sender"

    def receiver_obj(self, obj):
        if obj.receiver:
            url = reverse("admin:user_user_change", args=[obj.receiver.id])
            return format_html('<a href="{}">{}</a>', url, obj.receiver.username)
        return "N/A"
    receiver_obj.short_description = "Receiver"


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "user_obj", "title", "text", "created_time"]
    search_fields = ["user__first_name", "user__last_name", "title"]
    list_per_page = 10
    ordering = ['-created_time']

    def user_obj(self, obj):
        if obj.user:
            url = reverse("admin:user_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
        return "N/A"
    user_obj.short_description = "User"


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ["id", "name",]
    search_fields = ["id", "name",]


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "region"]
    search_fields = ["id", "name", "region__name"]
    list_filter = ["region"]


@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "district"]
    search_fields = ["id", "name", "district__name"]
    list_filter = ["district"]
