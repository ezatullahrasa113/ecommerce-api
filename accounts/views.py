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



class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    throttle_classes = [RegisterRateThrottle]
    permission_classes = [AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


    def get_object(self):
        return self.request.user

class LoginView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle]

class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

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

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "Password changed successfully."
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

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