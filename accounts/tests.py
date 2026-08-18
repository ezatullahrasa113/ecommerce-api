from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache

from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

from accounts.tokens import email_verification_token
from django.core import mail

from products.models import Category, Product

from decimal import Decimal



User = get_user_model()


class RegisterTests(APITestCase):
    url = "/api/accounts/register/"

    def setUp(self):
        cache.clear()

    def test_valid_registration(self):
        data = {
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            User.objects.filter(email="newuser@example.com").exists()
        )

    def test_duplicate_email(self):
        User.objects.create_user(
            email="existing@example.com",
            password="StrongPassword123!",
        )

        data = {
            "email": "existing@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_mismatch(self):
        data = {
            "email": "user@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "DifferentPassword123!",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn(
            "Passwords do not match.",
            response.data["error"]["fields"]["password"],
        )

    def test_password_too_short(self):
        data = {
            "email": "short@example.com",
            "password": "123",
            "password_confirm": "123",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_email(self):
        data = {
            "email": "not-an-email",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_is_hashed(self):
        password = "StrongPassword123!"

        data = {
            "email": "hashed@example.com",
            "password": password,
            "password_confirm": password,
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(email="hashed@example.com")

        self.assertNotEqual(user.password, password)
        self.assertTrue(user.check_password(password))



# Login Test
class LoginTests(APITestCase):
    url = "/api/accounts/login/"

    def setUp(self):
        self.email = "user@example.com"
        self.password = "StrongPassword123!"

        self.user = User.objects.create_user(
            email=self.email,
            password=self.password,
        )

    def test_successful_login(self):
        data = {
            "email": self.email,
            "password": self.password,
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_wrong_password(self):
        data = {
            "email": self.email,
            "password": "WrongPassword123!",
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_wrong_email(self):
        data = {
            "email": "wrong@example.com",
            "password": self.password,
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class MeTests(APITestCase):
    url = "/api/accounts/me/"

    def setUp(self):
        self.password = "StrongPassword123!"

        self.user = User.objects.create_user(
            email="user@example.com",
            password=self.password,
            first_name="Ezatullah",
            last_name="Rasa",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="OtherPassword123!",
            first_name="Other",
            last_name="User",
        )

    def authenticate(self, user=None):
        user = user or self.user

        refresh = RefreshToken.for_user(user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

    def test_authenticated_user_can_view_profile(self):
        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["email"],
            self.user.email,
        )

        self.assertEqual(
            response.data["first_name"],
            self.user.first_name,
        )

    def test_unauthenticated_user_gets_401(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_user_can_update_profile(self):
        self.authenticate()

        data = {
            "first_name": "NewName",
            "last_name": "UpdatedName",
        }

        response = self.client.patch(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.first_name,
            "NewName",
        )

        self.assertEqual(
            self.user.last_name,
            "UpdatedName",
        )

    def test_user_can_only_view_their_own_profile(self):
        self.authenticate(self.user)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["email"],
            self.user.email,
        )

        self.assertNotEqual(
            response.data["email"],
            self.other_user.email,
        )


class LogoutTests(APITestCase):
    url = "/api/accounts/logout/"
    refresh_url = "/api/accounts/token/refresh/"

    def setUp(self):
        self.password = "StrongPassword123!"

        self.user = User.objects.create_user(
            email="logout@example.com",
            password=self.password,
        )

        self.refresh = RefreshToken.for_user(self.user)

        self.refresh_token = str(self.refresh)
        self.access_token = str(self.refresh.access_token)

    def authenticate(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

    def test_valid_refresh_token_logout(self):
        self.authenticate()

        response = self.client.post(
            self.url,
            {
                "refresh": self.refresh_token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_205_RESET_CONTENT,
        )

        self.assertEqual(
            response.data["detail"],
            "Successfully logged out.",
        )

    def test_blacklisted_token_cannot_refresh(self):
        self.authenticate()

        # Logout first
        logout_response = self.client.post(
            self.url,
            {
                "refresh": self.refresh_token,
            },
            format="json",
        )

        self.assertEqual(
            logout_response.status_code,
            status.HTTP_205_RESET_CONTENT,
        )

        # Try to use the same refresh token again
        response = self.client.post(
            self.refresh_url,
            {
                "refresh": self.refresh_token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_invalid_refresh_token_rejected(self):
        self.authenticate()

        response = self.client.post(
            self.url,
            {
                "refresh": "this-is-not-a-valid-refresh-token",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_unauthenticated_user_cannot_logout(self):
        # No Authorization header
        response = self.client.post(
            self.url,
            {
                "refresh": self.refresh_token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class ChangePasswordTests(APITestCase):
    url = "/api/accounts/change-password/"

    def setUp(self):
        self.old_password = "StrongPassword123!"
        self.new_password = "NewStrongPassword456!"

        self.user = User.objects.create_user(
            email="password@example.com",
            password=self.old_password,
        )

        refresh = RefreshToken.for_user(self.user)

        self.access_token = str(refresh.access_token)

    def authenticate(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

    def test_authenticated_user_can_change_password(self):
        self.authenticate()

        response = self.client.post(
            self.url,
            {
                "old_password": self.old_password,
                "new_password": self.new_password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(self.new_password)
        )

    def test_wrong_old_password(self):
        self.authenticate()

        response = self.client.post(
            self.url,
            {
                "old_password": "WrongPassword123!",
                "new_password": self.new_password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(self.old_password)
        )

    def test_weak_new_password(self):
        self.authenticate()

        response = self.client.post(
            self.url,
            {
                "old_password": self.old_password,
                "new_password": "123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(self.old_password)
        )

    def test_unauthenticated_user(self):
        response = self.client.post(
            self.url,
            {
                "old_password": self.old_password,
                "new_password": self.new_password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_old_password_no_longer_works(self):
        self.authenticate()

        response = self.client.post(
            self.url,
            {
                "old_password": self.old_password,
                "new_password": self.new_password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.check_password(self.old_password)
        )

    def test_new_password_works(self):
        self.authenticate()

        response = self.client.post(
            self.url,
            {
                "old_password": self.old_password,
                "new_password": self.new_password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(self.new_password)
        )

class ThrottleTests(APITestCase):

    def setUp(self):
        cache.clear()

        self.password = "StrongPassword123!"

        self.user = User.objects.create_user(
            email="throttle@example.com",
            password=self.password,
        )

        self.login_url = "/api/accounts/login/"

    def test_login_rate_limit(self):
        data = {
            "email": self.user.email,
            "password": self.password,
        }

        responses = []

        for _ in range(6):
            response = self.client.post(
                self.login_url,
                data,
                format="json",
            )

            responses.append(response.status_code)

        self.assertEqual(
            responses[:5],
            [status.HTTP_200_OK] * 5,
        )

        self.assertEqual(
            responses[5],
            status.HTTP_429_TOO_MANY_REQUESTS,
        )


    def test_register_rate_limit(self):
        cache.clear()

        url = "/api/accounts/register/"

        for i in range(3):
            data = {
                "email": f"rate{i}@example.com",
                "password": "StrongPassword123!",
                "password_confirm": "StrongPassword123!",
            }

            response = self.client.post(
                url,
                data,
                format="json",
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
            )

        # 4th request should be blocked
        data = {
            "email": "rate3@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        response = self.client.post(
            url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )



class EmailVerificationTests(APITestCase):

    url = "/api/accounts/email-verify/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="verify@example.com",
            password="StrongPassword123!",
        )

        self.uid = urlsafe_base64_encode(
            force_bytes(self.user.pk)
        )

        self.token = email_verification_token.make_token(
            self.user
        )

    def test_valid_verification(self):
        response = self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": self.token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.is_verified
        )

    def test_invalid_uid(self):
        response = self.client.post(
            self.url,
            {
                "uid": "invalid-uid",
                "token": self.token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_invalid_token(self):
        response = self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": "invalid-token",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.is_verified
        )

    def test_already_verified_user(self):
        self.user.is_verified = True
        self.user.save()

        response = self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": self.token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_token_cannot_be_reused(self):
        # First verification
        response = self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": self.token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        # Try the same token again
        response = self.client.post(
            self.url,
            {
                "uid": self.uid,
                "token": self.token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


class RegistrationVerificationTests(APITestCase):

    register_url = "/api/accounts/register/"
    verify_url = "/api/accounts/email-verify/"

    def setUp(self):
        cache.clear()
        mail.outbox.clear()

    def register_user(self):
        data = {
            "email": "verification@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        return self.client.post(
            self.register_url,
            data,
            format="json",
        )

    def test_new_user_is_unverified(self):
        response = self.register_user()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = User.objects.get(
            email="verification@example.com"
        )

        self.assertFalse(
            user.is_verified
        )

    def test_verification_email_is_sent(self):
        response = self.register_user()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )

        email = mail.outbox[0]

        self.assertEqual(
            email.to,
            ["verification@example.com"],
        )

        self.assertEqual(
            email.subject,
            "Verify your email",
        )

    def test_email_contains_uid(self):
        response = self.register_user()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = User.objects.get(
            email="verification@example.com"
        )

        uid = urlsafe_base64_encode(
            force_bytes(user.pk)
        )

        email_body = mail.outbox[0].body

        self.assertIn(
            uid,
            email_body,
        )

    def test_email_contains_token(self):
        response = self.register_user()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = User.objects.get(
            email="verification@example.com"
        )

        token = email_verification_token.make_token(
            user
        )

        email_body = mail.outbox[0].body

        self.assertIn(
            token,
            email_body,
        )

    def test_verification_makes_user_active(self):
        response = self.register_user()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = User.objects.get(
            email="verification@example.com"
        )

        uid = urlsafe_base64_encode(
            force_bytes(user.pk)
        )

        token = email_verification_token.make_token(
            user
        )

        response = self.client.post(
            self.verify_url,
            {
                "uid": uid,
                "token": token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        user.refresh_from_db()

        self.assertTrue(
            user.is_verified
        )



User = get_user_model()

class ProductPermissionTests(APITestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics",
            description="Electronic products",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Laptop",
            description="A powerful laptop",
            price=Decimal("1000.00"),
            stock=10,
        )

        self.customer = User.objects.create_user(
            email="customer@example.com",
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

        self.list_url = "/api/products/products/"
        self.detail_url = f"/api/products/products/{self.product.slug}/"

    def authenticate(self, user):
        refresh = RefreshToken.for_user(user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

    def product_data(self):
        return {
            "category_id": self.category.pk,
            "name": "Phone",
            "description": "A smartphone",
            "price": Decimal("500.00"),
            "stock": 20,
            "is_active": True,
        }

    def test_anonymous_can_view_products(self):
        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_customer_can_view_products(self):
        self.authenticate(self.customer)

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


    def test_staff_can_create_product(self):
        self.authenticate(self.staff)

        response = self.client.post(
            self.list_url,
            self.product_data(),
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    
    def test_admin_can_create_product(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.list_url,
            self.product_data(),
            format="json",
        )

        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )


    def test_customer_cannot_create_product(self):
        self.authenticate(self.customer)

        response = self.client.post(
            self.list_url,
            self.product_data(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_customer_cannot_update_product(self):
        self.authenticate(self.customer)

        response = self.client.patch(
            self.detail_url,
            {
                "price": Decimal("700.00"),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )


    def test_customer_cannot_delete_product(self):
        self.authenticate(self.customer)

        response = self.client.delete(
            self.detail_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_can_update_product(self):
        self.authenticate(self.staff)

        response = self.client.patch(
            self.detail_url,
            {
                "price":Decimal("800.00") ,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.price,
            Decimal("800.00"),
        )


    def test_staff_can_delete_product(self):
        self.authenticate(self.staff)

        response = self.client.delete(
            self.detail_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Product.objects.filter(
                pk=self.product.pk
            ).exists()
        )

    