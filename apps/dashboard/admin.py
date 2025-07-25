from django.contrib import admin

from apps.dashboard.models import (
    PrivacyPolicy,
    TermsOfCondition
)


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "language"]
    search_fields = ["title",]
    fields = ["language", "title", "text"]


@admin.register(TermsOfCondition)
class TermsOfConditionAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "language"]
    search_fields = ["title",]
    fields = ["language", "title", "text"]
