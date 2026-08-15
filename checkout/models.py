from django.conf import settings
from django.db import models


class CheckoutRequest(models.Model):

    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="checkout_requests",
    )

    idempotency_key = models.CharField(
        max_length=255,
    )

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="checkout_request",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING,
    )

    failure_reason = models.TextField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "idempotency_key",
                ],
                name="unique_user_idempotency_key",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "idempotency_key",
                ],
                name="checkout_user_idem_idx",
            ),
        ]

        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.user} - "
            f"{self.idempotency_key} - "
            f"{self.status}"
        )