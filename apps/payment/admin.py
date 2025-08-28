from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.payment.models import Transaction


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
