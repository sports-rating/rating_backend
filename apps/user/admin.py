from django.contrib import admin
from django.utils.html import format_html

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "username",
        "phone_number",
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
                    "last_name",
                    "phone_number",
                    "is_verified",
                )
            },
        ),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "user_permissions")}),
    )
    filter_horizontal = ("user_permissions",)