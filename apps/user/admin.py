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
    Neighborhood,
)
from apps.shared.utils.general import get_file_full_url
from apps.shared.utils.general import calculate_file_size


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
    search_fields = ["username", "phone_number", "first_name", "last_name", "pinfl"]
    list_filter = ["is_verified",]
    readonly_fields = ["created_time", "educations", "results", "profile", "federation", "profile_picture"]
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
                    "email",
                    "is_verified",
                    "user_role",
                    "region",
                    "district",
                    "profile_picture",
                    "educations",
                    "results",
                    "profile",
                    "federation",
                )
            },
        ),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "user_permissions")}),
    )
    filter_horizontal = ("user_permissions",)
    list_per_page = 10

    @admin.display(description="Educations")
    def educations(self, obj):
        """Display educations as clickable links."""
        links = [
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:career_education_change", args=[edu.id]),
                str(edu),
            )
            for edu in obj.educations.all()
        ]
        return format_html("<br>".join(links)) if links else "N/A"

    @admin.display(description="Results")
    def results(self, obj):
        """Display results as clickable links."""
        links = [
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:career_result_change", args=[res.id]),
                str(res),
            )
            for res in obj.results.all()
        ]
        return format_html("<br>".join(links)) if links else "N/A"

    @admin.display(description="Profile")
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
        return "N/A"

    @admin.display(description="Federation")
    def federation(self, obj):
        if obj.user_role == "trainer" and hasattr(obj, 'trainer_profile') and obj.trainer_profile and obj.trainer_profile.federation:
            url = reverse("admin:federation_federation_change", args=[obj.trainer_profile.federation.id])
            return format_html('<a href="{}">{}</a>', url, obj.trainer_profile.federation.name)
        elif obj.user_role == "sportsman" and hasattr(obj, 'sportsman_profile') and obj.sportsman_profile and obj.sportsman_profile.trainer:
            if obj.sportsman_profile.trainer.federation:
                url = reverse("admin:federation_federation_change", args=[obj.sportsman_profile.trainer.federation.id])
                return format_html('<a href="{}">{}</a>', url, obj.sportsman_profile.trainer.federation.name)
        return "N/A"

    @admin.display(description="Profile Picture")
    def profile_picture(self, obj):
        if hasattr(obj, 'media') and obj.media:
            profile_pic = obj.media.filter(is_profile_photo=True).first()
            if profile_pic:
                return format_html(
                    '<a href="{}" target="_blank">{}</a>',
                    get_file_full_url(profile_pic.file),
                    get_file_full_url(profile_pic.file)
                )
        return "N/A"


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
                    "division",
                    "sport_rank",
                    "points",
                    "bio",
                    "is_result_paid",
                )
            },
        ),
        ("User Metrics", {"fields": ("user_metrics", "height", "weight")}),
        ("Adress", {"fields": ("address",)}),
        ("Social media", {"fields": ("social_media",)}),
        # ("Media", {"fields": ("media",)}),

    )
    list_filter = ["sport_rank",]


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
                    "points",
                    "federation",
                    "bio",
                )
            },
        ),
        ("User Metrics", {"fields": ("user_metrics", "height", "weight")}),
        ("Adress", {"fields": ("address",)}),
        ("Social media", {"fields": ("social_media",)}),
        # ("Media", {"fields": ("media",)}),

    )
    list_filter = ["skill_level",]


@admin.register(UserMedia)
class UserMediaAdmin(admin.ModelAdmin):
    list_display = ["id", "media_type", "size", "extension", "created_time"]
    list_filter = ["media_type", "extension"]
    search_fields = ["id", "file", "extension"]
    ordering = ["-created_time"]
    readonly_fields = ["file_size", "created_time", "updated_time"]

    @admin.display(description="File Size")
    def file_size(self, obj):
        return calculate_file_size(obj.size)


@admin.register(ArchivedTrainer)
class ArchivedTrainerAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]


@admin.register(UserRequest)
class UserRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "sender_obj", "receivers_obj", "request_type", "status"]
    search_fields = ['sender__first_name', 'sender__last_name']
    list_per_page = 10
    ordering = ['-created_time']
    readonly_fields = ["sender_obj", "receivers_obj", "processed_by_obj", "created_time", "updated_time"]

    @admin.display(description="Sender")
    def sender_obj(self, obj):
        if obj.sender:
            url = reverse("admin:user_user_change", args=[obj.sender.id])
            return format_html('<a href="{}">{}</a>', url, obj.sender.username)
        return "N/A"

    @admin.display(description="Receivers")
    def receivers_obj(self, obj):
        if obj.receivers.exists():
            urls = [
                reverse("admin:user_user_change", args=[receiver.id])
                for receiver in obj.receivers.all()
            ]
            return format_html('<br>'.join(f'<a href="{url}">{receiver.username}</a>' for url, receiver in zip(urls, obj.receivers.all())))
        return "N/A"

    @admin.display(description="Processed By")
    def processed_by_obj(self, obj):
        if obj.processed_by:
            url = reverse("admin:user_user_change", args=[obj.processed_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.processed_by.full_name)
        return "N/A"


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
