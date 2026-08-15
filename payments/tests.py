from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from orders.models import Order,OrderItem
from products.models import Product,Category
from .models import Payment
from .services import PaymentError

from payments.services import (
    PaymentService,
    OrderNotFoundError,
    PaymentNotFoundError,
    PaymentValidationError,
    PaymentStateError,
)


from django.db import close_old_connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient,APITestCase
from unittest.mock import patch
import threading
from rest_framework import status




User = get_user_model()


class PaymentModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="StrongPass123",
        )

        self.order = Order.objects.create(
            user=self.user,
            status=Order.Status.PENDING,
            total_price=Decimal("1000.00"),
        )

    def create_payment(self, **kwargs):
        defaults = {
            "order": self.order,
            "user": self.user,
            "amount": Decimal("1000.00"),
            "currency": "USD",
            "payment_method": Payment.PaymentMethod.CARD,
        }

        defaults.update(kwargs)

        return Payment.objects.create(**defaults)

    # =====================================================
    # Creation
    # =====================================================

    def test_payment_can_be_created(self):

        payment = self.create_payment()

        self.assertIsNotNone(payment.pk)

        self.assertEqual(
            payment.order,
            self.order,
        )

        self.assertEqual(
            payment.user,
            self.user,
        )

        self.assertEqual(
            payment.amount,
            Decimal("1000.00"),
        )

        self.assertEqual(
            payment.currency,
            "USD",
        )

    # =====================================================
    # Default status
    # =====================================================

    def test_payment_default_status_is_pending(self):

        payment = self.create_payment()

        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )

    # =====================================================
    # Payment methods
    # =====================================================

    def test_payment_can_use_card(self):

        payment = self.create_payment(
            payment_method=Payment.PaymentMethod.CARD,
        )

        self.assertEqual(
            payment.payment_method,
            Payment.PaymentMethod.CARD,
        )

    def test_payment_can_use_bank_transfer(self):

        payment = self.create_payment(
            payment_method=Payment.PaymentMethod.BANK_TRANSFER,
        )

        self.assertEqual(
            payment.payment_method,
            Payment.PaymentMethod.BANK_TRANSFER,
        )

    def test_payment_can_use_cash(self):

        payment = self.create_payment(
            payment_method=Payment.PaymentMethod.CASH,
        )

        self.assertEqual(
            payment.payment_method,
            Payment.PaymentMethod.CASH,
        )

    # =====================================================
    # Transaction ID
    # =====================================================

    def test_transaction_id_can_be_empty(self):

        payment = self.create_payment()

        self.assertIsNone(
            payment.transaction_id,
        )

    def test_transaction_id_must_be_unique(self):

        self.create_payment(
            transaction_id="txn-123",
        )

        with self.assertRaises(IntegrityError):

            self.create_payment(
                transaction_id="txn-123",
            )

    # =====================================================
    # Failure reason
    # =====================================================

    def test_failure_reason_can_be_stored(self):

        payment = self.create_payment(
            status=Payment.Status.FAILED,
            failure_reason="Payment was declined.",
        )

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

        self.assertEqual(
            payment.failure_reason,
            "Payment was declined.",
        )

    def test_failure_reason_is_empty_by_default(self):

        payment = self.create_payment()

        self.assertIsNone(
            payment.failure_reason,
        )

    # =====================================================
    # Multiple payments
    # =====================================================

    def test_order_can_have_multiple_payments(self):

        payment1 = self.create_payment(
            status=Payment.Status.FAILED,
            failure_reason="Payment declined.",
        )

        payment2 = self.create_payment(
            status=Payment.Status.SUCCEEDED,
            transaction_id="txn-456",
        )

        self.assertEqual(
            self.order.payments.count(),
            2,
        )

        self.assertEqual(
            payment1.order,
            self.order,
        )

        self.assertEqual(
            payment2.order,
            self.order,
        )

    # =====================================================
    # Status changes
    # =====================================================

    def test_payment_status_can_change(self):

        payment = self.create_payment()

        payment.status = Payment.Status.PROCESSING

        payment.save(
            update_fields=["status"],
        )

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.PROCESSING,
        )

        payment.status = Payment.Status.SUCCEEDED

        payment.save(
            update_fields=["status"],
        )

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCEEDED,
        )

    # =====================================================
    # Refund status
    # =====================================================

    def test_payment_can_be_refunded(self):

        payment = self.create_payment(
            status=Payment.Status.REFUNDED,
            transaction_id="txn-refund-123",
        )

        self.assertEqual(
            payment.status,
            Payment.Status.REFUNDED,
        )

    # =====================================================
    # Relationships
    # =====================================================

    def test_user_can_access_payments(self):

        payment = self.create_payment()

        self.assertIn(
            payment,
            self.user.payments.all(),
        )

    def test_order_can_access_payments(self):

        payment = self.create_payment()

        self.assertIn(
            payment,
            self.order.payments.all(),
        )



class PaymentServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="StrongPass123",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123",
        )

        self.order = Order.objects.create(
            user=self.user,
            status=Order.Status.PENDING,
            total_price=Decimal("1000.00"),
        )

    # =====================================================
    # Successful payment creation
    # =====================================================

    def test_create_payment_successfully(self):

        payment = PaymentService.create_payment(
            user=self.user,
            order_id=self.order.id,
            payment_method=Payment.PaymentMethod.CARD,
        )

        self.assertIsNotNone(
            payment.pk,
        )

        self.assertEqual(
            payment.order,
            self.order,
        )

        self.assertEqual(
            payment.user,
            self.user,
        )

        self.assertEqual(
            payment.amount,
            Decimal("1000.00"),
        )

        self.assertEqual(
            payment.currency,
            "USD",
        )

        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )

    # =====================================================
    # Order not found
    # =====================================================

    def test_payment_fails_when_order_does_not_exist(self):

        with self.assertRaises(
            OrderNotFoundError
        ):

            PaymentService.create_payment(
                user=self.user,
                order_id=999999,
                payment_method=Payment.PaymentMethod.CARD,
            )

    # =====================================================
    # Ownership
    # =====================================================

    def test_user_cannot_pay_another_users_order(self):

        with self.assertRaises(
            PaymentValidationError
        ) as context:

            PaymentService.create_payment(
                user=self.other_user,
                order_id=self.order.id,
                payment_method=Payment.PaymentMethod.CARD,
            )

        self.assertEqual(
            str(context.exception),
            "You cannot pay for this order.",
        )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    # =====================================================
    # Order status
    # =====================================================

    def test_payment_fails_for_non_pending_order(self):

        self.order.status = Order.Status.CONFIRMED

        self.order.save(
            update_fields=["status"],
        )

        with self.assertRaises(
            PaymentValidationError
        ) as context:

            PaymentService.create_payment(
                user=self.user,
                order_id=self.order.id,
                payment_method=Payment.PaymentMethod.CARD,
            )

        self.assertEqual(
            str(context.exception),
            "This order cannot be paid.",
        )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    # =====================================================
    # Amount comes from order
    # =====================================================

    def test_payment_amount_comes_from_order(self):

        self.order.total_price = Decimal("1250.50")

        self.order.save(
            update_fields=["total_price"],
        )

        payment = PaymentService.create_payment(
            user=self.user,
            order_id=self.order.id,
            payment_method=Payment.PaymentMethod.CARD,
        )

        self.assertEqual(
            payment.amount,
            Decimal("1250.50"),
        )

    # =====================================================
    # Existing successful payment
    # =====================================================

    def test_cannot_pay_already_paid_order(self):

        Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=Decimal("1000.00"),
            currency="USD",
            payment_method=Payment.PaymentMethod.CARD,
            status=Payment.Status.SUCCEEDED,
            transaction_id="txn-123",
        )

        with self.assertRaises(
            PaymentValidationError
        ) as context:

            PaymentService.create_payment(
                user=self.user,
                order_id=self.order.id,
                payment_method=Payment.PaymentMethod.CARD,
            )

        self.assertEqual(
            str(context.exception),
            "This order has already been paid.",
        )

        self.assertEqual(
            Payment.objects.count(),
            1,
        )

    # =====================================================
    # Failed payment can be retried
    # =====================================================

    def test_failed_payment_allows_new_payment_attempt(self):

        Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=Decimal("1000.00"),
            currency="USD",
            payment_method=Payment.PaymentMethod.CARD,
            status=Payment.Status.FAILED,
            failure_reason="Payment declined.",
        )

        payment = PaymentService.create_payment(
            user=self.user,
            order_id=self.order.id,
            payment_method=Payment.PaymentMethod.CARD,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )

        self.assertEqual(
            Payment.objects.count(),
            2,
        )




class PaymentProcessingTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            email="customer@example.com",
            password="StrongPass123",
        )

        self.order = Order.objects.create(
            user=self.user,
            status=Order.Status.PENDING,
            total_price=Decimal("1000.00"),
        )

        self.payment = Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=Decimal("1000.00"),
            currency="USD",
            payment_method=Payment.PaymentMethod.CARD,
            status=Payment.Status.PENDING,
        )

    # =====================================================
    # Successful payment
    # =====================================================

    def test_complete_payment_marks_payment_as_succeeded(self):

        payment = PaymentService.complete_payment(
            payment_id=self.payment.id,
            transaction_id="txn-success-123",
        )

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCEEDED,
        )

        self.assertEqual(
            payment.transaction_id,
            "txn-success-123",
        )

    def test_complete_payment_confirms_order(self):

        PaymentService.complete_payment(
            payment_id=self.payment.id,
            transaction_id="txn-success-123",
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CONFIRMED,
        )

    def test_successful_payment_clears_failure_reason(self):

        self.payment.failure_reason = "Previous error"
        self.payment.save(
            update_fields=["failure_reason"],
        )

        PaymentService.complete_payment(
            payment_id=self.payment.id,
            transaction_id="txn-success-123",
        )

        self.payment.refresh_from_db()

        self.assertIsNone(
            self.payment.failure_reason,
        )

    # =====================================================
    # Failed payment
    # =====================================================

    def test_fail_payment_marks_payment_as_failed(self):

        payment = PaymentService.fail_payment(
            payment_id=self.payment.id,
            failure_reason="Card was declined.",
        )

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

        self.assertEqual(
            payment.failure_reason,
            "Card was declined.",
        )

    def test_failed_payment_does_not_confirm_order(self):

        PaymentService.fail_payment(
            payment_id=self.payment.id,
            failure_reason="Card was declined.",
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.PENDING,
        )

    # =====================================================
    # Invalid transitions
    # =====================================================

    def test_failed_payment_cannot_be_completed(self):

        self.payment.status = Payment.Status.FAILED
        self.payment.failure_reason = "Card declined."

        self.payment.save(
            update_fields=[
                "status",
                "failure_reason",
            ]
        )

        with self.assertRaises(
            PaymentStateError
        ):

            PaymentService.complete_payment(
                payment_id=self.payment.id,
                transaction_id="txn-123",
            )

    def test_successful_payment_cannot_be_failed(self):

        self.payment.status = Payment.Status.SUCCEEDED
        self.payment.transaction_id = "txn-success"

        self.payment.save(
            update_fields=[
                "status",
                "transaction_id",
            ]
        )

        with self.assertRaises(
            PaymentStateError
        ):

            PaymentService.fail_payment(
                payment_id=self.payment.id,
                failure_reason="Something went wrong.",
            )

    def test_successful_payment_cannot_be_completed_again(self):

        self.payment.status = Payment.Status.SUCCEEDED
        self.payment.transaction_id = "txn-success"

        self.payment.save(
            update_fields=[
                "status",
                "transaction_id",
            ]
        )

        with self.assertRaises(
            PaymentStateError
        ):

            PaymentService.complete_payment(
                payment_id=self.payment.id,
                transaction_id="txn-another",
            )

    # =====================================================
    # Missing payment
    # =====================================================

    def test_complete_payment_fails_when_payment_does_not_exist(self):

        with self.assertRaises(
            PaymentNotFoundError
        ):

            PaymentService.complete_payment(
                payment_id=999999,
                transaction_id="txn-123",
            )

    def test_fail_payment_fails_when_payment_does_not_exist(self):

        with self.assertRaises(
            PaymentNotFoundError
        ):

            PaymentService.fail_payment(
                payment_id=999999,
                failure_reason="Payment failed.",
            )



class PaymentVerificationAPITests(APITestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="StrongPass123",
        )

        self.other_customer = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123",
        )

        self.category = Category.objects.create(
            name="Electronics",
        )

        self.product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=self.category,
        )

        self.order = Order.objects.create(
            user=self.customer,
            status=Order.Status.PENDING,
            total_price=Decimal("1000.00"),
        )

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            product_price=self.product.price,
            quantity=1,
        )

        self.payment = Payment.objects.create(
            order=self.order,
            user=self.customer,
            amount=Decimal("1000.00"),
            currency="USD",
            payment_method="mock",
            status=Payment.Status.PENDING,
        )

        self.other_order = Order.objects.create(
            user=self.other_customer,
            status=Order.Status.PENDING,
            total_price=Decimal("1000.00"),
        )

        self.other_payment = Payment.objects.create(
            order=self.other_order,
            user=self.other_customer,
            amount=Decimal("1000.00"),
            currency="USD",
            payment_method="mock",
            status=Payment.Status.PENDING,
        )

        self.url = "/api/payments/"

    def verify(self, payment_id, transaction_id):
        return self.client.post(
            f"{self.url}{payment_id}/verify/",
            {
                "transaction_id": transaction_id,
            },
            format="json",
        )

    # =====================================================
    # Authentication
    # =====================================================

    def test_unauthenticated_user_cannot_verify_payment(self):

        response = self.verify(
            self.payment.id,
            "txn-success-123",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # =====================================================
    # Payment lookup / authorization
    # =====================================================

    def test_payment_not_found(self):

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            999999,
            "txn-success-123",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            response.data["detail"],
            "Payment not found.",
        )

    def test_user_cannot_verify_another_users_payment(self):

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.other_payment.id,
            "txn-success-123",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.other_payment.refresh_from_db()

        self.assertEqual(
            self.other_payment.status,
            Payment.Status.PENDING,
        )

        self.other_order.refresh_from_db()

        self.assertEqual(
            self.other_order.status,
            Order.Status.PENDING,
        )

    # =====================================================
    # Validation
    # =====================================================

    def test_transaction_id_is_required(self):

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.post(
            f"{self.url}{self.payment.id}/verify/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Transaction ID is required.",
        )

    # =====================================================
    # Successful verification
    # =====================================================

    def test_successful_payment_verification(self):

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "txn-success-123",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.SUCCEEDED,
        )

    def test_successful_verification_saves_transaction_id(self):

        self.client.force_authenticate(
            user=self.customer,
        )

        transaction_id = "txn-success-456"

        response = self.verify(
            self.payment.id,
            transaction_id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.transaction_id,
            transaction_id,
        )

    def test_successful_verification_confirms_order(self):

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "txn-order-confirm-123",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CONFIRMED,
        )

    def test_successful_verification_clears_failure_reason(self):

        self.payment.failure_reason = (
            "Previous temporary failure."
        )

        self.payment.save(
            update_fields=["failure_reason"]
        )

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "txn-success-789",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.payment.refresh_from_db()

        self.assertIsNone(
            self.payment.failure_reason,
        )

    # =====================================================
    # Provider failure
    # =====================================================

    def test_provider_failure_returns_bad_request(self):

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "fail-provider-123",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Payment verification failed.",
        )

    def test_provider_failure_marks_payment_failed(self):

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "fail-provider-456",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.FAILED,
        )

    def test_provider_failure_saves_failure_reason(self):

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "fail-provider-789",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.failure_reason,
            "Payment verification failed.",
        )

    def test_provider_failure_does_not_confirm_order(self):

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "fail-provider-order",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.PENDING,
        )

    # =====================================================
    # Amount verification
    # =====================================================

    @patch(
        "payments.services.MockPaymentProvider.verify"
    )
    def test_amount_mismatch_fails_payment(
        self,
        mock_verify,
    ):

        mock_verify.return_value = {
            "success": True,
            "transaction_id": "txn-wrong-amount",
            "amount": Decimal("500.00"),
        }

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "txn-wrong-amount",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Payment amount does not match.",
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.FAILED,
        )

        self.assertEqual(
            self.payment.failure_reason,
            "Payment amount does not match.",
        )

    def test_successful_payment_uses_provider_transaction_id(self):

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "txn-provider-123",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.transaction_id,
            "txn-provider-123",
        )

    # =====================================================
    # Payment state protection
    # =====================================================

    def test_successful_payment_cannot_be_verified_again(self):

        self.payment.status = Payment.Status.SUCCEEDED
        self.payment.transaction_id = "txn-original"

        self.payment.save(
            update_fields=[
                "status",
                "transaction_id",
            ]
        )

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "txn-another",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Payment has already succeeded.",
        )

    def test_failed_payment_cannot_be_verified(self):

        self.payment.status = Payment.Status.FAILED
        self.payment.failure_reason = (
            "Previous payment failure."
        )

        self.payment.save(
            update_fields=[
                "status",
                "failure_reason",
            ]
        )

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "txn-retry",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "A failed payment cannot be completed.",
        )

    def test_refunded_payment_cannot_be_verified(self):

        self.payment.status = Payment.Status.REFUNDED

        self.payment.save(
            update_fields=["status"]
        )

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "txn-refunded",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "A refunded payment cannot be completed.",
        )

    def test_payment_cannot_confirm_non_pending_order(self):

        self.order.status = Order.Status.PROCESSING

        self.order.save(
            update_fields=["status"]
        )

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.verify(
            self.payment.id,
            "txn-non-pending",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "The order cannot be confirmed.",
        )




class PaymentVerificationConcurrencyTests(TransactionTestCase):

    reset_sequences = True

    def setUp(self):

        self.customer = User.objects.create_user(
            email="concurrent-payment@example.com",
            password="StrongPass123",
        )

        self.category = Category.objects.create(
            name="Electronics",
        )

        self.product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=self.category,
        )

        self.order = Order.objects.create(
            user=self.customer,
            status=Order.Status.PENDING,
            total_price=Decimal("1000.00"),
        )

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            product_price=self.product.price,
            quantity=1,
        )

        self.payment = Payment.objects.create(
            order=self.order,
            user=self.customer,
            amount=Decimal("1000.00"),
            currency="USD",
            payment_method="mock",
            status=Payment.Status.PENDING,
        )

    def test_concurrent_payment_verification(self):

        barrier = threading.Barrier(2)

        results = []

        def verify_payment():

            close_old_connections()

            try:

                barrier.wait()

                payment = PaymentService.complete_payment(
                    payment_id=self.payment.id,
                    transaction_id="txn-concurrent",
                )

                results.append(
                    (
                        "success",
                        payment.status,
                    )
                )

            except PaymentError as exc:

                results.append(
                    (
                        "error",
                        str(exc),
                    )
                )

            finally:

                close_old_connections()

        thread1 = threading.Thread(
            target=verify_payment
        )

        thread2 = threading.Thread(
            target=verify_payment
        )

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        self.assertEqual(
            len(results),
            2,
        )

        success_count = sum(
            1
            for result in results
            if result[0] == "success"
        )

        error_count = sum(
            1
            for result in results
            if result[0] == "error"
        )

        self.assertEqual(
            success_count,
            1,
        )

        self.assertEqual(
            error_count,
            1,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.SUCCEEDED,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            Payment.objects.filter(
                status=Payment.Status.SUCCEEDED
            ).count(),
            1,
        )