from django.db import transaction

from orders.models import Order

from .models import Payment
from .providers import (
MockPaymentProvider,
PaymentProviderError,
)

class PaymentError(Exception):
    """Base exception for payment errors."""

class OrderNotFoundError(PaymentError):
    """Raised when the order does not exist."""

class PaymentNotFoundError(PaymentError):
    """Raised when the payment does not exist."""

class PaymentValidationError(PaymentError):
    """Raised when payment validation fails."""

class PaymentStateError(PaymentError):
    """Raised when an invalid payment state transition is attempted."""

class PaymentService:

    # =====================================================
    # Create payment
    # =====================================================

    @staticmethod
    def create_payment(
        *,
        user,
        order_id,
        payment_method,
    ):

        if not payment_method:
            raise PaymentValidationError(
                "Payment method is required."
            )

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

            # ---------------------------------------------
            # Verify ownership
            # ---------------------------------------------

            if order.user_id != user.id:

                raise PaymentValidationError(
                    "You cannot pay for this order."
                )

            # ---------------------------------------------
            # Order must be pending
            # ---------------------------------------------

            if order.status != Order.Status.PENDING:

                raise PaymentValidationError(
                    "This order cannot be paid."
                )

            # ---------------------------------------------
            # Check successful payment
            # ---------------------------------------------

            successful_payment = (
                Payment.objects
                .filter(
                    order=order,
                    status=Payment.Status.SUCCEEDED,
                )
                .first()
            )

            if successful_payment:

                raise PaymentValidationError(
                    "This order has already been paid."
                )

            # ---------------------------------------------
            # Create payment
            # ---------------------------------------------

            payment = Payment.objects.create(
                order=order,
                user=user,
                amount=order.total_price,
                currency="USD",
                payment_method=payment_method,
                status=Payment.Status.PENDING,
            )

            return payment

    # =====================================================
    # Verify / complete payment
    # =====================================================

    @staticmethod
    def complete_payment(
        *,
        payment_id,
        transaction_id,
    ):

        if not transaction_id:
            raise PaymentValidationError(
                "Transaction ID is required."
            )

        validation_error = None
        completed_payment = None

        with transaction.atomic():

            # ---------------------------------------------
            # Lock payment
            # ---------------------------------------------

            try:

                payment = (
                    Payment.objects
                    .select_for_update()
                    .select_related("order")
                    .get(id=payment_id)
                )

            except Payment.DoesNotExist:

                raise PaymentNotFoundError(
                    "Payment not found."
                )

            # ---------------------------------------------
            # Lock order
            # ---------------------------------------------

            order = (
                Order.objects
                .select_for_update()
                .get(id=payment.order_id)
            )

            # ---------------------------------------------
            # Already successful
            # ---------------------------------------------

            if payment.status == Payment.Status.SUCCEEDED:

                raise PaymentStateError(
                    "Payment has already succeeded."
                )

            # ---------------------------------------------
            # Failed payment
            # ---------------------------------------------

            if payment.status == Payment.Status.FAILED:

                raise PaymentStateError(
                    "A failed payment cannot be completed."
                )

            # ---------------------------------------------
            # Refunded payment
            # ---------------------------------------------

            if payment.status == Payment.Status.REFUNDED:

                raise PaymentStateError(
                    "A refunded payment cannot be completed."
                )

            # ---------------------------------------------
            # Order must still be pending
            # ---------------------------------------------

            if order.status != Order.Status.PENDING:

                raise PaymentStateError(
                    "The order cannot be confirmed."
                )

            # ---------------------------------------------
            # Provider verification
            # ---------------------------------------------

            try:

                result = MockPaymentProvider.verify(
                    transaction_id=transaction_id,
                    amount=payment.amount,
                )

            except PaymentProviderError as exc:

                payment.status = Payment.Status.FAILED
                payment.failure_reason = str(exc)

                payment.save(
                    update_fields=[
                        "status",
                        "failure_reason",
                        "updated_at",
                    ]
                )

                validation_error = PaymentValidationError(
                    str(exc)
                )

            else:

                # -----------------------------------------
                # Provider says verification failed
                # -----------------------------------------

                if not result.get("success"):

                    payment.status = Payment.Status.FAILED
                    payment.failure_reason = (
                        "Payment verification failed."
                    )

                    payment.save(
                        update_fields=[
                            "status",
                            "failure_reason",
                            "updated_at",
                        ]
                    )

                    validation_error = PaymentValidationError(
                        "Payment verification failed."
                    )

                # -----------------------------------------
                # Amount mismatch
                # -----------------------------------------

                elif result.get("amount") != payment.amount:

                    payment.status = Payment.Status.FAILED
                    payment.failure_reason = (
                        "Payment amount does not match."
                    )

                    payment.save(
                        update_fields=[
                            "status",
                            "failure_reason",
                            "updated_at",
                        ]
                    )

                    validation_error = PaymentValidationError(
                        "Payment amount does not match."
                    )

                else:

                    # -------------------------------------
                    # Successful payment
                    # -------------------------------------

                    payment.status = Payment.Status.SUCCEEDED

                    payment.transaction_id = result.get(
                        "transaction_id"
                    )

                    payment.failure_reason = None

                    payment.save(
                        update_fields=[
                            "status",
                            "transaction_id",
                            "failure_reason",
                            "updated_at",
                        ]
                    )

                    # -------------------------------------
                    # Confirm order
                    # -------------------------------------

                    order.status = Order.Status.CONFIRMED

                    order.save(
                        update_fields=[
                            "status",
                            "updated_at",
                        ]
                    )

                    completed_payment = payment

        # =================================================
        # Raise AFTER transaction commits
        # =================================================

        if validation_error:
            raise validation_error

        return completed_payment



     # =====================================================
    # Payment failure
    # =====================================================

    @staticmethod
    def fail_payment(
        *,
        payment_id,
        failure_reason,
    ):

        if not failure_reason:
            raise PaymentValidationError(
                "Failure reason is required."
            )

        with transaction.atomic():

            # ---------------------------------------------
            # Get and lock payment
            # ---------------------------------------------

            try:
                payment = (
                    Payment.objects
                    .select_for_update()
                    .get(id=payment_id)
                )

            except Payment.DoesNotExist:

                raise PaymentNotFoundError(
                    "Payment not found."
                )

            # ---------------------------------------------
            # Successful payment cannot be failed
            # ---------------------------------------------

            if payment.status == Payment.Status.SUCCEEDED:

                raise PaymentStateError(
                    "A successful payment cannot be failed."
                )

            # ---------------------------------------------
            # Refunded payment cannot be failed
            # ---------------------------------------------

            if payment.status == Payment.Status.REFUNDED:

                raise PaymentStateError(
                    "A refunded payment cannot be failed."
                )

            # ---------------------------------------------
            # Already failed
            # ---------------------------------------------

            if payment.status == Payment.Status.FAILED:

                raise PaymentStateError(
                    "Payment has already failed."
                )

            # ---------------------------------------------
            # Mark payment as failed
            # ---------------------------------------------

            payment.status = Payment.Status.FAILED
            payment.failure_reason = failure_reason

            payment.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "updated_at",
                ]
            )

            return payment