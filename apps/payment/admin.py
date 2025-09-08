from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.payment.models import (
    Transaction,
    SectionPayment,
    SectionFee
)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "transaction_type", "status", "amount", "payment_method", "created_time"]
    search_fields = ["transaction_id", "user__username", "user__email"]
    list_filter = ["payme_state", "status", "payment_method", "performed_time", "cancelled_time"]
    readonly_fields = ["created_time", "updated_time", "payment_details", "cancel_reason", "user_obj"]

    @admin.display(description="User obj")
    def user_obj(self, obj: Transaction) -> str:
        """Display a link to the user associated with this transaction"""
        if obj.user:
            return format_html(
                '<a href="{}">{}</a>',
                reverse("admin:user_user_change", args=[obj.user.id]),
                str(obj.user.username)
            )
        return "-"


@admin.register(SectionPayment)
class SectionPaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "section_fee", "is_paid", "paid_at", "created_time"]
    search_fields = ["user__username", "user__email", "section_fee__section"]
    list_filter = ["is_paid", "section_fee"]
    readonly_fields = ["created_time", "updated_time"]

    @admin.display(description="User obj")
    def user_obj(self, obj: SectionPayment) -> str:
        """Display a link to the user associated with this section payment"""
        if obj.user:
            return format_html(
                '<a href="{}">{}</a>',
                reverse("admin:user_user_change", args=[obj.user.id]),
                str(obj.user.username)
            )
        return "-"


@admin.register(SectionFee)
class SectionFeeAdmin(admin.ModelAdmin):
    list_display = ["id", "section", "amount", "created_time"]
    search_fields = ["section"]
    readonly_fields = ["created_time", "updated_time"]
