from django.db import transaction

from .models import Order


class OrderStatusError(Exception):
    """Base exception for order status errors."""


class OrderNotFoundError(OrderStatusError):
    """Raised when the order does not exist."""


class InvalidOrderTransitionError(OrderStatusError):
    """Raised when an invalid status transition is requested."""


class OrderService:

    # =====================================================
    # Allowed status transitions
    # =====================================================

    ALLOWED_TRANSITIONS = {
        Order.Status.PENDING: {
            Order.Status.CANCELLED,
        },

        Order.Status.CONFIRMED: {
            Order.Status.PROCESSING,
            Order.Status.CANCELLED,
        },

        Order.Status.PROCESSING: {
            Order.Status.SHIPPED,
        },

        Order.Status.SHIPPED: {
            Order.Status.DELIVERED,
        },

        Order.Status.DELIVERED: set(),

        Order.Status.CANCELLED: set(),
    }

    # =====================================================
    # Change order status
    # =====================================================

    @staticmethod
    def change_status(
        *,
        order_id,
        new_status,
    ):

        with transaction.atomic():

            try:

                order = (
                    Order.objects
                    .select_for_update()
                    .get(id=order_id)
                )

            except Order.DoesNotExist:

                raise OrderNotFoundError(
                    "Order not found."
                )

            current_status = order.status

            allowed_statuses = (
                OrderService.ALLOWED_TRANSITIONS.get(
                    current_status,
                    set(),
                )
            )

            if new_status not in allowed_statuses:

                raise InvalidOrderTransitionError(
                    f"Cannot change order status "
                    f"from {current_status} "
                    f"to {new_status}."
                )

            order.status = new_status

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            return order