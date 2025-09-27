from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html


from apps.career.models import (
    Education,
    WorkPlace,
    Result
)


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ["id", "sport", "start_year", "end_year"]


@admin.register(WorkPlace)
class WorkPlaceAdmin(admin.ModelAdmin):
    list_display = ['id', 'trainer_obj', 'school_obj', 'sport_obj', 'created_time']
    search_fields = ['trainer__user__first_name', 'trainer__user__last_name', 'federation__name', 'school__name', 'sport__name']
    list_per_page = 10
    ordering = ['-created_time']
    readonly_fields = ['trainer_obj', 'school_obj', 'sport_obj']

    @admin.display(description="Trainer")
    def trainer_obj(self, obj: WorkPlace) -> str:
        if obj.trainer and obj.trainer.user:
            url = reverse("admin:user_user_change", args=[obj.trainer.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.trainer.user.get_full_name())
        return "N/A"

    # @admin.display(description="Federation")
    # def federation_obj(self, obj: WorkPlace) -> str:
    #     if obj.federation:
    #         url = reverse("admin:federation_federation_change", args=[obj.federation.id])
    #         return format_html('<a href="{}">{}</a>', url, obj.federation.name)
    #     return "N/A"

    @admin.display(description="School")
    def school_obj(self, obj: WorkPlace) -> str:
        if obj.school:
            url = reverse("admin:sport_school_change", args=[obj.school.id])
            return format_html('<a href="{}">{}</a>', url, obj.school.name)
        return "N/A"

    @admin.display(description="Sport")
    def sport_obj(self, obj: WorkPlace) -> str:
        if obj.sport:
            url = reverse("admin:sport_sport_change", args=[obj.sport.id])
            return format_html('<a href="{}">{}</a>', url, obj.sport.name)
        return "N/A"


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ["id", "tournament", "year", "currently_participating"]
    list_filter = ["currently_participating",]
