from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):

    model = OrderItem

    extra = 0

    fields = [
        "product",
        "product_name",
        "product_price",
        "quantity",
        "created_at",
    ]

    readonly_fields = [
        "product_name",
        "product_price",
        "created_at",
    ]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = [
        "id",
        "user",
        "status",
        "total_price",
        "created_at",
        "updated_at",
    ]

    list_filter = [
        "status",
        "created_at",
    ]

    search_fields = [
        "user__email",
        "id",
    ]

    ordering = [
        "-created_at",
    ]

    readonly_fields = [
        "user",
        "total_price",
        "created_at",
        "updated_at",
    ]

    inlines = [
        OrderItemInline,
    ]

    list_select_related = [
        "user",
    ]