from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem

        fields = [
            "id",
            "product",
            "product_name",
            "product_price",
            "quantity",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "product_name",
            "product_price",
            "created_at",
        ]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Quantity must be at least 1."
            )

        return value



class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Order

        fields = [
            "id",
            "user",
            "status",
            "total_price",
            "items",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "user",
            "status",
            "total_price",
            "items",
            "created_at",
            "updated_at",
        ]