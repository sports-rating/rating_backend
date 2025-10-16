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
    list_display = ["id", "trainer", "sport", "sport_institution", "created_time"]
    search_fields = ["trainer__user__first_name", "trainer__user__last_name", "sport__name", "sport_institution__name"]
    list_per_page = 10
    ordering = ['-created_time']
    readonly_fields = ['user_obj', 'trainer_obj', 'sport_institution_obj', 'sport_obj']

    @admin.display(description="User")
    def user_obj(self, obj: Education) -> str:
        if obj.user:
            url = reverse("admin:user_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
        return "N/A"

    @admin.display(description="Trainer")
    def trainer_obj(self, obj: Education) -> str:
        if obj.trainer and obj.trainer.user:
            url = reverse("admin:user_user_change", args=[obj.trainer.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.trainer.user.get_full_name())
        return "N/A"

    @admin.display(description="Sport Institution")
    def sport_institution_obj(self, obj: Education) -> str:
        if obj.sport_institution:
            url = reverse("admin:sport_sportinstitution_change", args=[obj.sport_institution.id])
            return format_html('<a href="{}">{}</a>', url, obj.sport_institution.name)
        return "N/A"

    @admin.display(description="Sport")
    def sport_obj(self, obj: Education) -> str:
        if obj.sport:
            url = reverse("admin:sport_sport_change", args=[obj.sport.id])
            return format_html('<a href="{}">{}</a>', url, obj.sport.name)
        return "N/A"


@admin.register(WorkPlace)
class WorkPlaceAdmin(admin.ModelAdmin):
    list_display = ['id', 'trainer_obj', 'sport_institution_obj', 'sport_obj', 'created_time']
    search_fields = ['trainer__user__first_name', 'trainer__user__last_name', 'federation__name', 'school__name', 'sport__name']
    list_per_page = 10
    ordering = ['-created_time']
    readonly_fields = ['trainer_obj', 'sport_institution_obj', 'sport_obj']

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

    @admin.display(description="Sport Institution")
    def sport_institution_obj(self, obj: WorkPlace) -> str:
        if obj.sport_institution:
            url = reverse("admin:sport_sportinstitution_change", args=[obj.sport_institution.id])
            return format_html('<a href="{}">{}</a>', url, obj.sport_institution.name)
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
    search_fields = ["tournament__name", "user__id", "user__first_name", "user__last_name", "trainer__user__first_name", "trainer__user__last_name"]
    list_per_page = 10
    ordering = ['-created_time']
    readonly_fields = ['trainer_obj', 'sportsman_obj', 'tournament_obj', 'request_obj']

    @admin.display(description="Trainer")
    def trainer_obj(self, obj: Result) -> str:
        if obj.trainer and obj.trainer.user:
            url = reverse("admin:user_user_change", args=[obj.trainer.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.trainer.user.get_full_name())
        return "N/A"

    @admin.display(description="Sportsman")
    def sportsman_obj(self, obj: Result) -> str:
        if obj.user:
            url = reverse("admin:user_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
        return "N/A"

    @admin.display(description="Tournament")
    def tournament_obj(self, obj: Result) -> str:
        if obj.tournament:
            url = reverse("admin:sport_tournament_change", args=[obj.tournament.id])
            return format_html('<a href="{}">{}</a>', url, obj.tournament.name)
        return "N/A"

    @admin.display(description="Associated Request")
    def request_obj(self, obj: Result) -> str:
        if obj.request:
            url = reverse("admin:user_userrequest_change", args=[obj.request.id])
            return format_html('<a href="{}">Request #{}</a>', url, obj.request.id)
        return "N/A"
