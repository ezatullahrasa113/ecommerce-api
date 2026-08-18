
from django.contrib import admin
from django.urls import path,include

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/products/',include('products.urls')),
    path('api/accounts/',include('accounts.urls')),
    path('api/cart/',include('cart.urls')),
    path('api/orders/',include('orders.urls')),
    path('api/checkout/',include('checkout.urls')),
    path('api/',include('payments.urls')),

# swagger
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),

    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema"
        ),
        name="swagger-ui",
    ),

    path(
        "api/redoc/",
        SpectacularRedocView.as_view(
            url_name="schema"
        ),
        name="redoc",
    ),

]


