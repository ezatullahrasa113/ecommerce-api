from rest_framework import serializers

from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment

        fields = [
            "id",
            "order",
            "amount",
            "currency",
            "payment_method",
            "status",
            "transaction_id",
            "failure_reason",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "order",
            "amount",
            "currency",
            "payment_method",
            "status",
            "transaction_id",
            "failure_reason",
            "created_at",
            "updated_at",
        ]


class PaymentCreateSerializer(serializers.Serializer):

    payment_method = serializers.CharField(
        max_length=50,
    )

class PaymentVerifySerializer(serializers.Serializer):

    transaction_id = serializers.CharField(
        max_length=255,
    )