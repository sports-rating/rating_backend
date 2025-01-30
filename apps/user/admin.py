from django.contrib import admin
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
    readonly_fields = ["created_time"]
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
                )
            },
        ),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "user_permissions")}),
    )
    filter_horizontal = ("user_permissions",)


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
    