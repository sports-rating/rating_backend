from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.review.models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "sport_institution", "created_time"]
    search_fields = ["user__first_name", "user__last_name"]
    readonly_fields = ["created_time", "user_obj", "sport_institution_obj"]
    list_filter = ["created_time"]

    @admin.display(description="User obj")
    def user_obj(self, obj):
        if obj.user:
            url = reverse("admin:user_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "N/A"

    @admin.display(description="Comment related object")
    def sport_institution_obj(self, obj):
        if obj.sport_institution:
            url = reverse(
                f"admin:sport_sportinstitution_change",
                args=[obj.sport_institution.id]
            )
            return format_html('<a href="{}">{}</a>', url, str(obj.sport_institution))
        return "N/A"
