from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = [
        "id",
        "user",
        "order",
        "amount",
        "currency",
        "payment_method",
        "status",
        "transaction_id",
        "created_at",
        "updated_at",
    ]

    list_filter = [
        "status",
        "payment_method",
        "currency",
        "created_at",
    ]

    search_fields = [
        "user__email",
        "transaction_id",
        "order__id",
    ]

    ordering = [
        "-created_at",
    ]

    readonly_fields = [
        "user",
        "order",
        "amount",
        "currency",
        "payment_method",
        "transaction_id",
        "failure_reason",
        "created_at",
        "updated_at",
    ]

    list_select_related = [
        "user",
        "order",
    ]