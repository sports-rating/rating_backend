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
    list_display = ["id", "user", "sport_type", "sport", "gender"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "sport_type",
                    "sport",
                    "motto",
                    "height",
                    "weight",
                )
            },
        ),
        ("Adress", {"fields": ("region", "city", "street", "place_of_birth", "citizenship", "moving_date")}),
        ("Contacts", {"fields": ("telegram", "instagram")}),
        ("Media", {"fields": ("media",)}),
        
    )
    list_filter = ["sport_type", "gender"]


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "sport_type", "sport","gender"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "sport_type",
                    "sport",
                    "motto",
                    "height",
                    "weight",
                    "number_of_games",
                    "number_of_students",
                    "number_of_awards",
                )
            },
        ),
        ("Adress", {"fields": ("region", "city", "street", "place_of_birth", "citizenship")}),
        ("Contacts", {"fields": ("telegram", "instagram")}),
        ("Media", {"fields": ("media",)}),
        
    )
    list_filter = ["sport_type", "gender"]


@admin.register(UserMedia)
class UserMediaAdmin(admin.ModelAdmin):
    list_display = ["id", "media_type", "size", "extension"]
    list_filter = ["media_type", "extension"]