from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from products.models import Product, Category
from .models import Order, OrderItem


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