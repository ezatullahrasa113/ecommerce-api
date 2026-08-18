from rest_framework import serializers


class CheckoutSerializer(serializers.Serializer):

    idempotency_key = serializers.CharField(
        max_length=255,
    )