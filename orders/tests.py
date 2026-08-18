from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from products.models import Product, Category
from .models import Order, OrderItem

from django.test import TestCase

from .models import Order
from .services import (
    InvalidOrderTransitionError,
    OrderNotFoundError,
    OrderService,
)


User = get_user_model()


class OrderAPITests(APITestCase):

    def setUp(self):
        # =========================
        # Users
        # =========================

        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="StrongPass123",
        )

        self.other_customer = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123",
        )

        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="StrongPass123",
            is_staff=True,
        )

        # =========================
        # Category
        # =========================

        self.category = Category.objects.create(
            name="Electronics",
        )

        # =========================
        # Products
        # =========================

        self.product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=self.category,
        )

        self.other_product = Product.objects.create(
            name="Mouse",
            price=Decimal("50.00"),
            category=self.category,
        )

        # =========================
        # Customer Order
        # =========================

        self.customer_order = Order.objects.create(
            user=self.customer,
            status=Order.Status.PENDING,
            total_price=Decimal("1050.00"),
        )

        # =========================
        # Customer Order Items
        # =========================

        OrderItem.objects.create(
            order=self.customer_order,
            product=self.product,
            product_name=self.product.name,
            product_price=self.product.price,
            quantity=1,
        )

        OrderItem.objects.create(
            order=self.customer_order,
            product=self.other_product,
            product_name=self.other_product.name,
            product_price=self.other_product.price,
            quantity=1,
        )

        # =========================
        # Other Customer's Order
        # =========================

        self.other_order = Order.objects.create(
            user=self.other_customer,
            status=Order.Status.PENDING,
            total_price=Decimal("1000.00"),
        )

        OrderItem.objects.create(
            order=self.other_order,
            product=self.product,
            product_name=self.product.name,
            product_price=self.product.price,
            quantity=1,
        )

        # =========================
        # API URL
        # =========================

        self.url_base = "/api/orders/"

    # =====================================================
    # Authentication
    # =====================================================

    def test_unauthenticated_user_cannot_access_orders(self):

        response = self.client.get(
            self.url_base
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # =====================================================
    # Customer permissions
    # =====================================================

    def test_customer_can_view_own_order(self):

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.get(
            f"{self.url_base}{self.customer_order.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.customer_order.id,
        )

    def test_customer_cannot_view_another_users_order(self):

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.get(
            f"{self.url_base}{self.other_order.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_customer_only_sees_own_orders(self):

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.get(
            self.url_base
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order_ids = [
            order["id"]
            for order in response.data
        ]

        self.assertIn(
            self.customer_order.id,
            order_ids,
        )

        self.assertNotIn(
            self.other_order.id,
            order_ids,
        )

    # =====================================================
    # Staff permissions
    # =====================================================

    def test_staff_can_view_any_order(self):

        self.client.force_authenticate(
            user=self.staff
        )

        response = self.client.get(
            f"{self.url_base}{self.other_order.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.other_order.id,
        )

    # =====================================================
    # Order details
    # =====================================================

    def test_order_contains_items(self):

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.get(
            f"{self.url_base}{self.customer_order.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "items",
            response.data,
        )

        self.assertEqual(
            len(response.data["items"]),
            2,
        )

        first_item = response.data["items"][0]

        self.assertIn(
            "product_name",
            first_item,
        )

        self.assertIn(
            "product_price",
            first_item,
        )

    # =====================================================
    # Order modification restrictions
    # =====================================================

    def test_customer_cannot_create_order_directly(self):

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.post(
            self.url_base,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_customer_cannot_update_order(self):

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.patch(
            f"{self.url_base}{self.customer_order.pk}/",
            {
                "status": "delivered",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_customer_cannot_delete_order(self):

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.delete(
            f"{self.url_base}{self.customer_order.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )




User = get_user_model()


class OrderStatusWorkflowTests(TestCase):

    def setUp(self):

        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="StrongPass123",
        )

        self.order = Order.objects.create(
            user=self.customer,
            status=Order.Status.PENDING,
            total_price="100.00",
        )

    # =====================================================
    # PENDING → CANCELLED
    # =====================================================

    def test_pending_order_can_be_cancelled(self):

        order = OrderService.change_status(
            order_id=self.order.id,
            new_status=Order.Status.CANCELLED,
        )

        self.assertEqual(
            order.status,
            Order.Status.CANCELLED,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CANCELLED,
        )

    # =====================================================
    # CONFIRMED → PROCESSING
    # =====================================================

    def test_confirmed_order_can_be_processing(self):

        self.order.status = Order.Status.CONFIRMED
        self.order.save(
            update_fields=["status"]
        )

        order = OrderService.change_status(
            order_id=self.order.id,
            new_status=Order.Status.PROCESSING,
        )

        self.assertEqual(
            order.status,
            Order.Status.PROCESSING,
        )

    # =====================================================
    # PROCESSING → SHIPPED
    # =====================================================

    def test_processing_order_can_be_shipped(self):

        self.order.status = Order.Status.PROCESSING
        self.order.save(
            update_fields=["status"]
        )

        order = OrderService.change_status(
            order_id=self.order.id,
            new_status=Order.Status.SHIPPED,
        )

        self.assertEqual(
            order.status,
            Order.Status.SHIPPED,
        )

    # =====================================================
    # SHIPPED → DELIVERED
    # =====================================================

    def test_shipped_order_can_be_delivered(self):

        self.order.status = Order.Status.SHIPPED
        self.order.save(
            update_fields=["status"]
        )

        order = OrderService.change_status(
            order_id=self.order.id,
            new_status=Order.Status.DELIVERED,
        )

        self.assertEqual(
            order.status,
            Order.Status.DELIVERED,
        )

    # =====================================================
    # CONFIRMED → CANCELLED
    # =====================================================

    def test_confirmed_order_can_be_cancelled(self):

        self.order.status = Order.Status.CONFIRMED
        self.order.save(
            update_fields=["status"]
        )

        order = OrderService.change_status(
            order_id=self.order.id,
            new_status=Order.Status.CANCELLED,
        )

        self.assertEqual(
            order.status,
            Order.Status.CANCELLED,
        )

    # =====================================================
    # Invalid transitions
    # =====================================================

    def test_pending_order_cannot_be_shipped(self):

        with self.assertRaises(
            InvalidOrderTransitionError
        ):

            OrderService.change_status(
                order_id=self.order.id,
                new_status=Order.Status.SHIPPED,
            )

    def test_pending_order_cannot_be_processing(self):

        with self.assertRaises(
            InvalidOrderTransitionError
        ):

            OrderService.change_status(
                order_id=self.order.id,
                new_status=Order.Status.PROCESSING,
            )

    def test_delivered_order_cannot_be_cancelled(self):

        self.order.status = Order.Status.DELIVERED
        self.order.save(
            update_fields=["status"]
        )

        with self.assertRaises(
            InvalidOrderTransitionError
        ):

            OrderService.change_status(
                order_id=self.order.id,
                new_status=Order.Status.CANCELLED,
            )

    def test_delivered_order_cannot_return_to_pending(self):

        self.order.status = Order.Status.DELIVERED
        self.order.save(
            update_fields=["status"]
        )

        with self.assertRaises(
            InvalidOrderTransitionError
        ):

            OrderService.change_status(
                order_id=self.order.id,
                new_status=Order.Status.PENDING,
            )

    def test_cancelled_order_cannot_be_processing(self):

        self.order.status = Order.Status.CANCELLED
        self.order.save(
            update_fields=["status"]
        )

        with self.assertRaises(
            InvalidOrderTransitionError
        ):

            OrderService.change_status(
                order_id=self.order.id,
                new_status=Order.Status.PROCESSING,
            )

    def test_shipped_order_cannot_return_to_processing(self):

        self.order.status = Order.Status.SHIPPED
        self.order.save(
            update_fields=["status"]
        )

        with self.assertRaises(
            InvalidOrderTransitionError
        ):

            OrderService.change_status(
                order_id=self.order.id,
                new_status=Order.Status.PROCESSING,
            )

    # =====================================================
    # Order not found
    # =====================================================

    def test_change_status_fails_when_order_does_not_exist(self):

        with self.assertRaises(
            OrderNotFoundError
        ):

            OrderService.change_status(
                order_id=999999,
                new_status=Order.Status.CANCELLED,
            )

    # =====================================================
    # Database persistence
    # =====================================================

    def test_status_change_is_persisted(self):

        OrderService.change_status(
            order_id=self.order.id,
            new_status=Order.Status.CANCELLED,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CANCELLED,
        )





class OrderStatusAPITests(APITestCase):

    def setUp(self):

        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="StrongPass123",
        )

        self.other_customer = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123",
        )

        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="StrongPass123",
            is_staff=True,
        )

        self.order = Order.objects.create(
            user=self.customer,
            status=Order.Status.PENDING,
            total_price="100.00",
        )

        self.other_order = Order.objects.create(
            user=self.other_customer,
            status=Order.Status.PENDING,
            total_price="100.00",
        )

        self.url = (
            f"/api/orders/{self.order.id}/status/"
        )

    # =====================================================
    # Authentication
    # =====================================================

    def test_unauthenticated_user_cannot_change_status(self):

        response = self.client.post(
            self.url,
            {
                "status": Order.Status.CANCELLED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # =====================================================
    # Customer cancellation
    # =====================================================

    def test_customer_can_cancel_own_pending_order(self):

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.post(
            self.url,
            {
                "status": Order.Status.CANCELLED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CANCELLED,
        )

    # =====================================================
    # Customer cannot fulfill order
    # =====================================================

    def test_customer_cannot_move_order_to_processing(self):

        self.order.status = Order.Status.CONFIRMED
        self.order.save(
            update_fields=["status"]
        )

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.post(
            self.url,
            {
                "status": Order.Status.PROCESSING,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_customer_cannot_move_order_to_shipped(self):

        self.order.status = Order.Status.PROCESSING
        self.order.save(
            update_fields=["status"]
        )

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.post(
            self.url,
            {
                "status": Order.Status.SHIPPED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_customer_cannot_move_order_to_delivered(self):

        self.order.status = Order.Status.SHIPPED
        self.order.save(
            update_fields=["status"]
        )

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.post(
            self.url,
            {
                "status": Order.Status.DELIVERED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    # =====================================================
    # Customer ownership
    # =====================================================

    def test_customer_cannot_change_another_users_order(self):

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.client.post(
            f"/api/orders/{self.other_order.id}/status/",
            {
                "status": Order.Status.CANCELLED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # =====================================================
    # Staff fulfillment
    # =====================================================

    def test_staff_can_confirmed_to_processing(self):

        self.order.status = Order.Status.CONFIRMED
        self.order.save(
            update_fields=["status"]
        )

        self.client.force_authenticate(
            user=self.staff
        )

        response = self.client.post(
            self.url,
            {
                "status": Order.Status.PROCESSING,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.PROCESSING,
        )

    def test_staff_can_processing_to_shipped(self):

        self.order.status = Order.Status.PROCESSING
        self.order.save(
            update_fields=["status"]
        )

        self.client.force_authenticate(
            user=self.staff
        )

        response = self.client.post(
            self.url,
            {
                "status": Order.Status.SHIPPED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.SHIPPED,
        )

    def test_staff_can_shipped_to_delivered(self):

        self.order.status = Order.Status.SHIPPED
        self.order.save(
            update_fields=["status"]
        )

        self.client.force_authenticate(
            user=self.staff
        )

        response = self.client.post(
            self.url,
            {
                "status": Order.Status.DELIVERED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.DELIVERED,
        )

    # =====================================================
    # Invalid transition through API
    # =====================================================

    def test_staff_cannot_skip_processing(self):

        self.order.status = Order.Status.CONFIRMED
        self.order.save(
            update_fields=["status"]
        )

        self.client.force_authenticate(
            user=self.staff
        )

        response = self.client.post(
            self.url,
            {
                "status": Order.Status.SHIPPED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # =====================================================
    # Missing status
    # =====================================================

    def test_status_is_required(self):

        self.client.force_authenticate(
            user=self.staff
        )

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )