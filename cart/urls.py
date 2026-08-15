from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MyCartView,
    CartDetailView,
    CartItemViewSet,
)




router = DefaultRouter()

router.register(
    "items",
    CartItemViewSet,
    basename="cart-item",
)

urlpatterns = [
    path(
        "",
        MyCartView.as_view(),
        name="my-cart",
    ),

    path(
        "<int:pk>/",
        CartDetailView.as_view(),
        name="cart-detail",
    ),

    path(
        "",
        include(router.urls),
    ),
]
