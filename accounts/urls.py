from django.urls import path
from .views import (
RegisterView,
 MeView,
 LogoutView,
 ChangePasswordView,
 LoginView,
 PasswordResetRequestView,
 PasswordResetConfirmView,
 EmailVerificationView,

)

from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),

    path('me/',MeView.as_view(),name = 'me'),

    path('logout/',LogoutView.as_view(), name = 'logout'),

    path('change-password/',ChangePasswordView.as_view(), name = 'change_password'),

    path("password-reset/",PasswordResetRequestView.as_view(),name="password_reset",),

    path("password-reset-confirm/",PasswordResetConfirmView.as_view(),name="password_reset_confirm",),

    path("email-verify/",EmailVerificationView.as_view(),name="email-verify",),


    
    # JWT
    path('login/', LoginView.as_view(), name='login'),

    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
