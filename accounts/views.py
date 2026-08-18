from rest_framework.permissions import AllowAny,IsAuthenticated

from .serializers import( 
RegisterSerializer,
UserSerializer,
PasswordResetConfirmSerializer,
PasswordResetRequestSerializer,
LogoutSerializer
)

from rest_framework.response import Response
from .serializers import ChangePasswordSerializer
from rest_framework import generics, status
from rest_framework_simplejwt.views import TokenObtainPairView
from .throttles import LoginRateThrottle,RegisterRateThrottle
from .serializers import EmailVerificationSerializer

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
)

    
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    throttle_classes = [RegisterRateThrottle]
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register a new user",
        description=(
            "Creates a new user account and sends an email "
            "verification link."
        ),
        request=RegisterSerializer,
        examples=[
            OpenApiExample(
                "Registration request",
                summary="Create a new account",
                description="Example registration data.",
                value={
                    "email": "customer@example.com",
                    "password": "StrongPassword123!",
                    "password_confirm": "StrongPassword123!",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Registration response",
                summary="Account created",
                value={
                    "id": 1,
                    "email": "customer@example.com",
                    "first_name": "",
                    "last_name": "",
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                "Password mismatch",
                summary="Passwords do not match",
                value={
                    "error": {
                        "detail": "Validation error.",
                        "fields": {
                            "password": [
                                "Passwords do not match."
                            ]
                        }
                    }
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
        responses={
            201: UserSerializer,
            400: OpenApiResponse(
                description="Invalid registration data."
            ),
        },
    )
    def post(self, request, *args, **kwargs):
            return super().post(request, *args, **kwargs)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    @extend_schema(
        summary="Get current user",
        description="Returns the authenticated user's profile.",
        responses={
            200: UserSerializer,
            401: OpenApiResponse(
                description="Authentication credentials were not provided or are invalid."
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update current user",
        description="Updates the authenticated user's profile.",
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(
                description="Invalid profile data."
            ),
            401: OpenApiResponse(
                description="Authentication required."
            ),
        },
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update current user",
        description="Partially updates the authenticated user's profile.",
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(
                description="Invalid profile data."
            ),
            401: OpenApiResponse(
                description="Authentication required."
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

class LoginView(TokenObtainPairView):

    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        summary="Login",
        description=(
            "Authenticates a user and returns an access token "
            "and refresh token."
        ),
        examples=[
            OpenApiExample(
                "Login request",
                summary="User login",
                value={
                    "email": "customer@example.com",
                    "password": "StrongPassword123!",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Login response",
                summary="JWT tokens",
                value={
                    "refresh": "eyJhbGciOiJIUzI1NiIs...",
                    "access": "eyJhbGciOiJIUzI1NiIs...",
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Invalid credentials",
                summary="Invalid email or password",
                value={
                    "error": {
                        "detail": "Authentication failed."
                    }
                },
                response_only=True,
                status_codes=["401"],
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Authentication successful."
            ),
            401: OpenApiResponse(
                description="Invalid email or password."
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
    summary="Logout",
    description=(
        "Blacklists the supplied refresh token and logs "
        "the authenticated user out."
    ),
    request=LogoutSerializer,
        examples=[
            OpenApiExample(
                "Logout request",
                summary="Blacklist refresh token",
                value={
                    "refresh": "eyJhbGciOiJIUzI1NiIs..."
                },
                request_only=True,
            ),
            OpenApiExample(
                "Logout response",
                summary="Successfully logged out",
                value={
                    "detail": "Successfully logged out."
                },
                response_only=True,
                status_codes=["205"],
            ),
            OpenApiExample(
                "Invalid refresh token",
                summary="Invalid refresh token",
                value={
                    "error": {
                        "detail": "Validation error.",
                        "fields": {
                            "refresh": [
                                "Invalid or expired refresh token."
                            ]
                        }
                    }
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
        responses={
            205: OpenApiResponse(
                description="Successfully logged out."
            ),
            400: OpenApiResponse(
                description="Invalid or expired refresh token."
            ),
            401: OpenApiResponse(
                description="Authentication required."
            ),
        },
    )


    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_205_RESET_CONTENT,
        )


class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change password",
        description="Changes the authenticated user's password.",
        request=ChangePasswordSerializer,
        examples=[
            OpenApiExample(
                "Change password request",
                summary="Change the current password",
                value={
                    "old_password": "OldPassword123!",
                    "new_password": "NewStrongPassword456!",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success response",
                value={
                    "detail": "Password changed successfully."
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Incorrect old password",
                value={
                    "error": {
                        "detail": "Validation error.",
                        "fields": {
                            "old_password": [
                                "Old password is incorrect."
                            ]
                        }
                    }
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Password changed successfully."
            ),
            400: OpenApiResponse(
                description="Invalid old password or new password."
            ),
            401: OpenApiResponse(
                description="Authentication required."
            ),
        },
    )
    def post(self, request):
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    @extend_schema(
            summary="Request password reset",
            description=(
                "Sends a password reset email to the specified "
                "email address."
            ),
            request=PasswordResetRequestSerializer,

            examples=[
                OpenApiExample(
                    "Password reset request",
                    value={
                        "email": "customer@example.com"
                    },
                    request_only=True,
                ),
                OpenApiExample(
                    "Password reset response",
                    value={
                        "detail": "Password reset email sent."
                    },
                    response_only=True,
                    status_codes=["200"],
                ),
            ],

            responses={
                200: OpenApiResponse(
                    description="Password reset email sent."
                ),
                400: OpenApiResponse(
                    description="Invalid email address."
                ),
            },
        )

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "Password reset email sent."
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    @extend_schema(
            summary="Confirm password reset",
            description=(
                "Validates the password reset token and sets "
                "a new password."
            ),
            request=PasswordResetConfirmSerializer,

            examples=[
                OpenApiExample(
                    "Password reset confirmation",
                    value={
                        "uid": "MQ",
                        "token": "example-reset-token",
                        "new_password": "NewStrongPassword456!",
                        "new_password_confirm": "NewStrongPassword456!",
                    },
                    request_only=True,
                ),
                OpenApiExample(
                    "Password reset success",
                    value={
                        "detail": "Password has been reset successfully."
                    },
                    response_only=True,
                    status_codes=["200"],
                ),
            ],

            responses={
                200: OpenApiResponse(
                    description="Password has been reset successfully."
                ),
                400: OpenApiResponse(
                    description="Invalid or expired reset token."
                ),
            },
        )

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "Password has been reset successfully."
            },
            status=status.HTTP_200_OK,
        )



class EmailVerificationView(generics.GenericAPIView):
    serializer_class = EmailVerificationSerializer
    permission_classes = [AllowAny]

    @extend_schema(
            summary="Verify email address",
            description=(
                "Verifies a user's email address using the "
                "UID and verification token."
            ),
            request=EmailVerificationSerializer,

            examples=[
                OpenApiExample(
                    "Email verification request",
                    value={
                        "uid": "MQ",
                        "token": "example-verification-token",
                    },
                    request_only=True,
                ),
                OpenApiExample(
                    "Verification success",
                    value={
                        "detail": "Email verified successfully."
                    },
                    response_only=True,
                    status_codes=["200"],
                ),
                OpenApiExample(
                    "Invalid verification token",
                    value={
                        "error": {
                            "detail": "Validation error.",
                            "fields": {
                                "detail": [
                                    "Invalid or expired verification token."
                                ]
                            }
                        }
                    },
                    response_only=True,
                    status_codes=["400"],
                ),
            ],
            
            responses={
                200: OpenApiResponse(
                    description="Email verified successfully."
                ),
                400: OpenApiResponse(
                    description="Invalid, expired, or already-used verification token."
                ),
            },
        )

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "Email verified successfully."
            },
            status=status.HTTP_200_OK,
        )