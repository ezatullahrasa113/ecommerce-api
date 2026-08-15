from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase
from decimal import Decimal

from cart.models import Cart, CartItem
from products.models import Product, Category
from orders.models import Order,OrderItem
from unittest.mock import patch
from .models import CheckoutRequest
from django.db import IntegrityError

import threading

from django.db import close_old_connections
from django.test import TransactionTestCase
from rest_framework.test import APITestCase, APIClient


User = get_user_model()


class CheckoutAPITests(APITestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="StrongPass123",
        )

        self.url = "/api/checkout/"

    def checkout(self, key="test-checkout-key"):
        return self.client.post(
            self.url,
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )

    def test_unauthenticated_user_cannot_checkout(self):

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_customer_without_cart_cannot_checkout(self):

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.checkout()

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            response.data["detail"],
            "Cart not found.",
        )



    def test_customer_cannot_checkout_empty_cart(self):

        self.client.force_authenticate(
            user=self.customer
        )

        Cart.objects.create(
            user=self.customer
        )

        response = self.checkout()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Your cart is empty.",
        )

        

    def test_customer_can_checkout_non_empty_cart(self):

        category = Category.objects.create(
            name="Electronics",
        )

        product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
            stock = 10,
        )

        cart = Cart.objects.create(
            user=self.customer
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=1,
        )

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.checkout()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["total_price"],
           "1000.00",
        )

        order = Order.objects.get(
            id=response.data["order_id"]
        )

        self.assertEqual(
            order.user,
            self.customer,
        )

        self.assertEqual(
            order.status,
            Order.Status.PENDING,
        )

        self.assertEqual(
            order.total_price,
            Decimal("1000.00"),
        )

    def test_checkout_creates_order_items(self):

        category = Category.objects.create(
            name="Electronics",
        )

        product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
             stock = 10,
        )

        cart = Cart.objects.create(
            user=self.customer
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=2,
        )

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.checkout()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order = Order.objects.get(
            id=response.data["order_id"]
        )

        order_item = OrderItem.objects.get(
            order=order
        )

        self.assertEqual(
            order_item.product,
            product,
        )

        self.assertEqual(
            order_item.product_name,
            "Laptop",
        )

        self.assertEqual(
            order_item.product_price,
            Decimal("1000.00"),
        )

        self.assertEqual(
            order_item.quantity,
            2,
        )



    def test_checkout_clears_cart(self):

        category = Category.objects.create(
            name="Electronics",
        )

        product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
             stock = 10,
        )

        cart = Cart.objects.create(
            user=self.customer
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=2,
        )

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.checkout()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            cart.items.count(),
            0,
        )


    def test_checkout_fails_when_stock_is_insufficient(self):

        category = Category.objects.create(
            name="Electronics",
        )

        product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
            stock=2,
        )

        cart = Cart.objects.create(
            user=self.customer
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=5,
        )

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.checkout()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "Insufficient stock",
            response.data["detail"],
        )



    def test_checkout_reduces_stock(self):

        category = Category.objects.create(
            name="Electronics",
        )

        product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
            stock=10,
        )

        cart = Cart.objects.create(
            user=self.customer
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=3,
        )

        self.client.force_authenticate(
            user=self.customer
        )

        response = self.checkout()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        product.refresh_from_db()

        self.assertEqual(
            product.stock,
            7,
        )


    def test_checkout_rolls_back_when_order_item_creation_fails(self):

        category = Category.objects.create(
            name="Electronics",
        )

        product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
            stock=2,
        )

        cart = Cart.objects.create(
            user=self.customer,
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=1,
        )

        self.client.force_authenticate(
            user=self.customer,
        )


        with patch(
            "checkout.services.OrderItem.objects.bulk_create",
            side_effect=Exception("Order item creation failed"),
        ):

            with self.assertRaises(Exception):
                self.checkout()

        # Order must be rolled back
        self.assertEqual(
            Order.objects.count(),
            0,
        )

        # Order items must be rolled back
        self.assertEqual(
            OrderItem.objects.count(),
            0,
        )

        # Stock must remain unchanged
        product.refresh_from_db()

        self.assertEqual(
            product.stock,
            2,
        )

        # Cart item must remain
        self.assertEqual(
            cart.items.count(),
            1,
        )


    def test_checkout_allows_purchase_when_stock_equals_quantity(self):

        category = Category.objects.create(
            name="Electronics",
        )

        product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
            stock=2,
        )

        cart = Cart.objects.create(
            user=self.customer,
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=2,
        )

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.checkout()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        product.refresh_from_db()

        self.assertEqual(
            product.stock,
            0,
        )


    def test_checkout_with_multiple_products(self):

        category = Category.objects.create(
            name="Electronics",
        )

        laptop = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
            stock=5,
        )

        mouse = Product.objects.create(
            name="Mouse",
            price=Decimal("50.00"),
            category=category,
            stock=10,
        )

        cart = Cart.objects.create(
            user=self.customer,
        )

        CartItem.objects.create(
            cart=cart,
            product=laptop,
            quantity=2,
        )

        CartItem.objects.create(
            cart=cart,
            product=mouse,
            quantity=3,
        )

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.checkout()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        # 2 × 1000 + 3 × 50
        self.assertEqual(
            response.data["total_price"],
            "2150.00",
        )

        order = Order.objects.get(
            id=response.data["order_id"]
        )

        self.assertEqual(
            order.total_price,
            Decimal("2150.00"),
        )

        # Two order items should have been created
        self.assertEqual(
            order.items.count(),
            2,
        )

        # Laptop stock: 5 - 2 = 3
        laptop.refresh_from_db()

        self.assertEqual(
            laptop.stock,
            3,
        )

        # Mouse stock: 10 - 3 = 7
        mouse.refresh_from_db()

        self.assertEqual(
            mouse.stock,
            7,
        )

        # Cart should be empty
        self.assertEqual(
            cart.items.count(),
            0,
        )



    def test_checkout_requires_idempotency_key(self):

        category = Category.objects.create(
            name="Electronics",
        )

        product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
            stock=10,
        )

        cart = Cart.objects.create(
            user=self.customer,
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=1,
        )

        self.client.force_authenticate(
            user=self.customer,
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

        self.assertEqual(
            response.data["detail"],
            "Idempotency-Key header is required.",
        )


    def test_checkout_with_idempotency_key_succeeds(self):

        category = Category.objects.create(
            name="Electronics",
        )

        product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
            stock=10,
        )

        cart = Cart.objects.create(
            user=self.customer,
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=1,
        )

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.post(
            self.url,
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="checkout-123",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["total_price"],
            "1000.00",
        )

        self.assertTrue(
            CheckoutRequest.objects.filter(
                user=self.customer,
                idempotency_key="checkout-123",
            ).exists()
        )

        self.assertEqual(
            Order.objects.count(),
            1,
        )



    def test_duplicate_idempotency_key_returns_same_order(self):

        category = Category.objects.create(
            name="Electronics",
        )

        product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
            stock=10,
        )

        cart = Cart.objects.create(
            user=self.customer,
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=1,
        )

        self.client.force_authenticate(
            user=self.customer,
        )

        response1 = self.client.post(
            self.url,
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="checkout-123",
        )

        self.assertEqual(
            response1.status_code,
            status.HTTP_201_CREATED,
        )

        order_id = response1.data["order_id"]

        # Send the same checkout request again
        response2 = self.client.post(
            self.url,
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="checkout-123",
        )

        self.assertEqual(
            response2.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response2.data["order_id"],
            order_id,
        )

        self.assertEqual(
            response2.data["total_price"],
            "1000.00",
        )

        # Only one order must exist
        self.assertEqual(
            Order.objects.count(),
            1,
        )

        # Only one CheckoutRequest must exist
        self.assertEqual(
            CheckoutRequest.objects.count(),
            1,
        )


    def test_idempotency_key_is_unique_per_user(self):

        CheckoutRequest.objects.create(
            user=self.customer,
            idempotency_key="checkout-123",
            order=Order.objects.create(
                user=self.customer,
                status=Order.Status.PENDING,
                total_price=Decimal("1000.00"),
            ),
        )

        order = Order.objects.create(
            user=self.customer,
            status=Order.Status.PENDING,
            total_price=Decimal("500.00"),
        )

        with self.assertRaises(IntegrityError):
            CheckoutRequest.objects.create(
                user=self.customer,
                idempotency_key="checkout-123",
                order=order,
            )

    def test_same_idempotency_key_allowed_for_different_users(self):

        second_customer = User.objects.create_user(
            email="second@example.com",
            password="StrongPass123",
        )

        order1 = Order.objects.create(
            user=self.customer,
            status=Order.Status.PENDING,
            total_price=Decimal("1000.00"),
        )

        order2 = Order.objects.create(
            user=second_customer,
            status=Order.Status.PENDING,
            total_price=Decimal("500.00"),
        )

        CheckoutRequest.objects.create(
            user=self.customer,
            idempotency_key="checkout-123",
            order=order1,
        )

        CheckoutRequest.objects.create(
            user=second_customer,
            idempotency_key="checkout-123",
            order=order2,
        )

        self.assertEqual(
            CheckoutRequest.objects.count(),
            2,
        )

    
    def test_checkout_fails_when_product_is_inactive(self):

        category = Category.objects.create(
            name="Electronics",
        )

        product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
            stock=10,
            is_active=False,
        )

        cart = Cart.objects.create(
            user=self.customer,
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=1,
        )

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.checkout()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "is no longer available",
            response.data["detail"],
        )

        # No order should be created
        self.assertEqual(
            Order.objects.count(),
            0,
        )

        # Stock must remain unchanged
        product.refresh_from_db()

        self.assertEqual(
            product.stock,
            10,
        )

        # Cart must remain unchanged
        self.assertEqual(
            cart.items.count(),
            1,
        )

        # Checkout request must not be completed
        self.assertEqual(
            CheckoutRequest.objects.count(),
            1,
        )


    def test_failed_checkout_can_be_retried(self):

        category = Category.objects.create(
            name="Electronics",
        )

        product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=category,
            stock=10,
            is_active=False,
        )

        cart = Cart.objects.create(
            user=self.customer,
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=1,
        )

        self.client.force_authenticate(
            user=self.customer,
        )

        # ---------------------------------------------
        # First attempt: product is inactive
        # ---------------------------------------------

        response1 = self.checkout(
            key="retry-checkout-123"
        )

        self.assertEqual(
            response1.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        checkout_request = CheckoutRequest.objects.get(
            user=self.customer,
            idempotency_key="retry-checkout-123",
        )

        self.assertEqual(
            checkout_request.status,
            CheckoutRequest.Status.FAILED,
        )

        self.assertIsNone(
            checkout_request.order
        )

        # ---------------------------------------------
        # Make product available
        # ---------------------------------------------

        product.is_active = True
        product.save(
            update_fields=["is_active"]
        )

        # ---------------------------------------------
        # Second attempt: same idempotency key
        # ---------------------------------------------

        response2 = self.checkout(
            key="retry-checkout-123"
        )

        self.assertEqual(
            response2.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response2.data["total_price"],
            "1000.00",
        )

        # ---------------------------------------------
        # Verify CheckoutRequest is completed
        # ---------------------------------------------

        checkout_request.refresh_from_db()

        self.assertEqual(
            checkout_request.status,
            CheckoutRequest.Status.COMPLETED,
        )

        self.assertIsNotNone(
            checkout_request.order
        )

        # ---------------------------------------------
        # Only one order should exist
        # ---------------------------------------------

        self.assertEqual(
            Order.objects.count(),
            1,
        )

        # ---------------------------------------------
        # Stock should be reduced once
        # ---------------------------------------------

        product.refresh_from_db()

        self.assertEqual(
            product.stock,
            9,
        )



class CheckoutConcurrencyTests(TransactionTestCase):

    reset_sequences = True

    def setUp(self):
        self.client = APIClient()

        self.customer = User.objects.create_user(
            email="concurrent@example.com",
            password="StrongPass123",
        )

        self.category = Category.objects.create(
            name="Electronics",
        )

        self.product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            category=self.category,
            stock=10,
        )

        self.cart = Cart.objects.create(
            user=self.customer,
        )

        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
        )

        self.url = "/api/checkout/"

    def checkout(self, key="test-checkout-key"):
        return self.client.post(
            self.url,
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )


    def test_same_idempotency_key_cannot_create_two_requests(self):

        order1 = Order.objects.create(
            user=self.customer,
            status=Order.Status.PENDING,
            total_price=Decimal("1000.00"),
        )

        CheckoutRequest.objects.create(
            user=self.customer,
            idempotency_key="concurrent-key",
            order=order1,
        )

        order2 = Order.objects.create(
            user=self.customer,
            status=Order.Status.PENDING,
            total_price=Decimal("1000.00"),
        )

        with self.assertRaises(IntegrityError):
            CheckoutRequest.objects.create(
                user=self.customer,
                idempotency_key="concurrent-key",
                order=order2,
            )


    def test_concurrent_duplicate_checkout_creates_one_order(self):

        idempotency_key = "concurrent-checkout-123"

        barrier = threading.Barrier(2)

        results = []

        def make_checkout_request():

            close_old_connections()

            client = APIClient()

            client.force_authenticate(
                user=self.customer
            )

            barrier.wait()

            response = client.post(
                self.url,
                {},
                format="json",
                HTTP_IDEMPOTENCY_KEY=idempotency_key,
            )

            results.append(
                (
                    response.status_code,
                    response.data,
                )
            )

            close_old_connections()

        thread1 = threading.Thread(
            target=make_checkout_request
        )

        thread2 = threading.Thread(
            target=make_checkout_request
        )

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Both requests should succeed
        self.assertEqual(
            len(results),
            2,
        )

        self.assertEqual(
            results[0][0],
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            results[1][0],
            status.HTTP_201_CREATED,
        )

        # Both requests must return the same order
        order_id_1 = results[0][1]["order_id"]
        order_id_2 = results[1][1]["order_id"]

        self.assertEqual(
            order_id_1,
            order_id_2,
        )

        # Only one Order must exist
        self.assertEqual(
            Order.objects.count(),
            1,
        )

        # Only one CheckoutRequest must exist
        self.assertEqual(
            CheckoutRequest.objects.count(),
            1,
        )

        # Stock must only be reduced once
        self.product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            9,
        )


    def test_failed_checkout_stores_failure_reason(self):

        self.product.is_active = False
        self.product.save(update_fields=["is_active"])

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.checkout(
            key="failure-reason-test",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        checkout_request = CheckoutRequest.objects.get(
            user=self.customer,
            idempotency_key="failure-reason-test",
        )

        self.assertEqual(
            checkout_request.status,
            CheckoutRequest.Status.FAILED,
        )

        self.assertEqual(
            checkout_request.failure_reason,
            "Laptop is no longer available.",
        )



    def test_retry_clears_failure_reason(self):

        self.product.is_active = False
        self.product.save(update_fields=["is_active"])

        self.client.force_authenticate(
            user=self.customer,
        )

        key = "failure-reason-retry"

        # First attempt fails
        response1 = self.checkout(key=key)

        self.assertEqual(
            response1.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        checkout_request = CheckoutRequest.objects.get(
            user=self.customer,
            idempotency_key=key,
        )

        self.assertEqual(
            checkout_request.status,
            CheckoutRequest.Status.FAILED,
        )

        self.assertIsNotNone(
            checkout_request.failure_reason,
        )

        # Make product available
        self.product.is_active = True
        self.product.save(
            update_fields=["is_active"]
        )

        # Retry
        response2 = self.checkout(key=key)

        self.assertEqual(
            response2.status_code,
            status.HTTP_201_CREATED,
        )

        checkout_request.refresh_from_db()

        self.assertEqual(
            checkout_request.status,
            CheckoutRequest.Status.COMPLETED,
        )

        self.assertIsNone(
            checkout_request.failure_reason,
        )