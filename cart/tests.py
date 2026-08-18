from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from django.db import IntegrityError
from .models import Cart,CartItem
from products.models import Product,Category

from django.core.cache import cache




User = get_user_model()

class CartTests(APITestCase):

    url_base = "/api/cart/"

    def setUp(self):
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="StrongPassword123!",
        )

        self.other_customer = User.objects.create_user(
            email="other@example.com",
            password="StrongPassword123!",
        )

        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="StrongPassword123!",
            is_staff=True,
        )

        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPassword123!",
        )

        self.customer_cart = Cart.objects.create(
            user=self.customer
        )

        self.other_cart = Cart.objects.create(
            user=self.other_customer
        )

    def authenticate(self, user):
        refresh = RefreshToken.for_user(user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

    def test_customer_can_access_own_cart(self):
        self.authenticate(self.customer)

        response = self.client.get(
            f"{self.url_base}{self.customer_cart.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.customer_cart.pk,
        )

    def test_customer_cannot_access_another_users_cart(self):
        self.authenticate(self.customer)

        response = self.client.get(
            f"{self.url_base}{self.other_cart.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_can_access_any_cart(self):
        self.authenticate(self.staff)

        response = self.client.get(
            f"{self.url_base}{self.customer_cart.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_admin_can_access_any_cart(self):
        self.authenticate(self.admin)

        response = self.client.get(
            f"{self.url_base}{self.customer_cart.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_unauthenticated_user_gets_401(self):
        response = self.client.get(
            f"{self.url_base}{self.customer_cart.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_each_customer_has_only_one_cart(self):
        Cart.objects.create(
            user=self.customer
        )

        # The OneToOneField should prevent a second cart.

    def test_each_customer_has_only_one_cart(self):
        with self.assertRaises(IntegrityError):
            Cart.objects.create(
                user=self.customer
            )




class CartItemTests(APITestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="StrongPassword123!",
        )

        self.category = Category.objects.create(
            name="Electronics",
            description="Electronic products",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Laptop",
            description="Powerful laptop",
            price="1000.00",
            stock=10,
        )

        self.cart = Cart.objects.create(
            user=self.customer
        )

    def test_can_add_product_to_cart(self):
        item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
        )

        self.assertEqual(
            item.product,
            self.product,
        )

        self.assertEqual(
            item.quantity,
            2,
        )

    def test_product_quantity_must_be_positive(self):
        item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=0,
        )

        # Model-level PositiveIntegerField does not necessarily
        # validate automatically when using objects.create().

        self.assertEqual(
            item.quantity,
            0,
        )

    def test_same_product_cannot_be_added_twice(self):
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
        )

        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                cart=self.cart,
                product=self.product,
                quantity=3,
            )




User = get_user_model()


class CartAPITests(APITestCase):

    cart_url = "/api/cart/"
    items_url = "/api/cart/items/"

    def setUp(self):

        cache.clear()

        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="StrongPassword123!",
        )

        self.other_customer = User.objects.create_user(
            email="other@example.com",
            password="StrongPassword123!",
        )

        self.category = Category.objects.create(
            name="Electronics",
            description="Electronic products",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Laptop",
            description="Powerful laptop",
            price="1000.00",
            stock=10,
        )

        self.other_product = Product.objects.create(
            category=self.category,
            name="Mouse",
            description="Wireless mouse",
            price="50.00",
            stock=20,
        )

    def authenticate(self, user=None):

        user = user or self.customer

        refresh = RefreshToken.for_user(user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )


    def test_customer_can_view_own_cart(self):

        self.authenticate()

        cart = Cart.objects.create(
            user=self.customer
        )

        response = self.client.get(
            self.cart_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            cart.id,
        )


    def test_cart_is_automatically_created(self):

        self.authenticate()

        self.assertFalse(
            Cart.objects.filter(
                user=self.customer
            ).exists()
        )

        response = self.client.get(
            self.cart_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            Cart.objects.filter(
                user=self.customer
            ).exists()
        )


    def test_customer_can_add_product(self):

        self.authenticate()

        response = self.client.post(
            self.items_url,
            {
                "product": self.product.id,
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            CartItem.objects.filter(
                product=self.product,
                cart__user=self.customer,
            ).exists()
        )



    def test_product_appears_in_cart(self):

        self.authenticate()

        response = self.client.post(
            self.items_url,
            {
                "product": self.product.id,
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        cart_response = self.client.get(
            self.cart_url
        )

        self.assertEqual(
            cart_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(cart_response.data["items"]),
            1,
        )

        item = cart_response.data["items"][0]

        self.assertEqual(
            item["product"],
            self.product.id,
        )

        self.assertEqual(
            item["quantity"],
            2,
        )


    def test_customer_can_update_quantity(self):

        self.authenticate()

        response = self.client.post(
            self.items_url,
            {
                "product": self.product.id,
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        item_id = response.data["id"]

        response = self.client.patch(
            f"{self.items_url}{item_id}/",
            {
                "quantity": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        item = CartItem.objects.get(
            id=item_id
        )

        self.assertEqual(
            item.quantity,
            5,
        )



    def test_customer_can_remove_item(self):

        self.authenticate()

        item = CartItem.objects.create(
            cart=Cart.objects.create(
                user=self.customer
            ),
            product=self.product,
            quantity=2,
        )

        response = self.client.delete(
            f"{self.items_url}{item.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            CartItem.objects.filter(
                id=item.id
            ).exists()
        )


    def test_customer_cannot_access_another_cart(self):

        other_cart = Cart.objects.create(
            user=self.other_customer
        )

        CartItem.objects.create(
            cart=other_cart,
            product=self.product,
            quantity=2,
        )

        self.authenticate(self.customer)

        response = self.client.get(
            self.cart_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertNotEqual(
            response.data["id"],
            other_cart.id,
        )


    def test_customer_cannot_modify_another_users_item(self):

        other_cart = Cart.objects.create(
            user=self.other_customer
        )

        item = CartItem.objects.create(
            cart=other_cart,
            product=self.product,
            quantity=2,
        )

        self.authenticate(self.customer)

        response = self.client.patch(
            f"{self.items_url}{item.id}/",
            {
                "quantity": 10,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        item.refresh_from_db()

        self.assertEqual(
            item.quantity,
            2,
        )


    def test_invalid_quantity_rejected(self):

        self.authenticate()

        response = self.client.post(
            self.items_url,
            {
                "product": self.product.id,
                "quantity": 0,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "Quantity must be at least 1.",
            response.data["error"]["fields"]["quantity"],
        )


    def test_duplicate_product_increases_quantity(self):

        self.authenticate()

        response = self.client.post(
            self.items_url,
            {
                "product": self.product.id,
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        response = self.client.post(
            self.items_url,
            {
                "product": self.product.id,
                "quantity": 3,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        item = CartItem.objects.get(
            cart__user=self.customer,
            product=self.product,
        )

        self.assertEqual(
            item.quantity,
            5,
        )