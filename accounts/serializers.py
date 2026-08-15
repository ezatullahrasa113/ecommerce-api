from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .tokens import email_verification_token



User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):

    password_confirm = serializers.CharField(
        write_only=True
    )

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "password_confirm",
        ]
        extra_kwargs = {
            "password": {
                "write_only": True,
            },
        }

    def validate(self, attrs):
        password = attrs["password"]
        password_confirm = attrs["password_confirm"]

        if password != password_confirm:
            raise serializers.ValidationError({
                "password": "Passwords do not match."
            })

        validate_password(password)

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")

        user = User.objects.create_user(
            **validated_data
        )

        user.is_verified = False
        user.save(update_fields=["is_verified"])

        # Generate verification data
        uid = urlsafe_base64_encode(
            force_bytes(user.pk)
        )

        token = email_verification_token.make_token(
            user
        )

        verification_url = (
            f"http://localhost:3000/verify-email/"
            f"{uid}/{token}/"
        )

        send_mail(
            subject="Verify your email",
            message=(
                "Welcome!\n\n"
                "Please verify your email using this link:\n"
                f"{verification_url}\n\n"
                "If you did not create this account, "
                "please ignore this email."
            ),
            from_email="webmaster@localhost",
            recipient_list=[user.email],
        )

        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
        ]

        read_only_fields = ['id','email']



class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs["refresh"]
        return attrs

    def save(self, **kwargs):
        try:
            refresh_token = RefreshToken(self.token)
            refresh_token.blacklist()
        except Exception:
            raise serializers.ValidationError(
                {"refresh": "Invalid or expired refresh token."}
            )



User = get_user_model()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        required=True,
    )

    new_password = serializers.CharField(
        write_only=True,
        required=True,
    )

    def validate_old_password(self, value):
        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError(
                "Old password is incorrect."
            )

        return value

    def validate_new_password(self, value):
        validate_password(
            value,
            self.context["request"].user,
        )

        return value

    def save(self, **kwargs):
        user = self.context["request"].user

        user.set_password(
            self.validated_data["new_password"]
        )

        user.save(
            update_fields=["password"]
        )

        return user


User = get_user_model()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No account exists with this email."
            )

        self.user = user
        return value

    def save(self):
        user = self.user

        uid = urlsafe_base64_encode(
            force_bytes(user.pk)
        )

        token = default_token_generator.make_token(user)

        reset_url = (
            f"http://localhost:3000/reset-password/"
            f"{uid}/{token}/"
        )

        send_mail(
            subject="Password Reset",
            message=(
                "You requested a password reset.\n\n"
                f"Reset your password here:\n{reset_url}\n\n"
                "If you did not request this, ignore this email."
            ),
            from_email=None,
            recipient_list=[user.email],
        )

        return user


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    new_password_confirm = serializers.CharField(
        write_only=True,
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({
                "new_password": "Passwords do not match."
            })

        try:
            uid = urlsafe_base64_decode(
                attrs["uid"]
            ).decode()
            
            user = User.objects.get(pk=uid)

        except (ValueError, TypeError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({
                "uid": "Invalid reset link."
            })

        if not default_token_generator.check_token(
            user,
            attrs["token"],
        ):
            raise serializers.ValidationError({
                "token": "Invalid or expired reset token."
            })

        attrs["user"] = user

        return attrs

    def save(self):
        user = self.validated_data["user"]

        user.set_password(
            self.validated_data["new_password"]
        )

        user.save(
            update_fields=["password"]
        )

        return user



User = get_user_model()


class EmailVerificationSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        try:
            uid = urlsafe_base64_decode(
                attrs["uid"]
            ).decode()
            user = User.objects.get(pk=uid)
        except (ValueError, TypeError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError(
                {"detail": "Invalid verification link."}
            )

        if user.is_verified:
            raise serializers.ValidationError(
                {"detail": "Email is already verified."}
            )

        if not email_verification_token.check_token(
            user,
            attrs["token"]
        ):
            raise serializers.ValidationError(
                {"detail": "Invalid or expired verification token."}
            )

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.is_verified = True
        user.save(update_fields=["is_verified"])

        return user