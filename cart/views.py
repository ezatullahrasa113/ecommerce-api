from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from .permissions import IsCartItemOwnerOrStaff,IsCartOwnerOrStaff



class MyCartView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def get_object(self):
        cart, created = Cart.objects.get_or_create(
            user=self.request.user
        )

        return cart


class CartDetailView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [
        IsAuthenticated,
        IsCartOwnerOrStaff,
    ]

    queryset = Cart.objects.all()


class CartItemViewSet(ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [
        IsAuthenticated,
        IsCartItemOwnerOrStaff,
    ]

    queryset = CartItem.objects.select_related(
        "cart",
        "product",
    )

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.is_superuser:
            return self.queryset

        return self.queryset.filter(
            cart__user=user
        )

    def perform_create(self, serializer):

        cart, created = Cart.objects.get_or_create(
            user=self.request.user
        )

        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                "quantity": quantity
            },
        )

        if not created:
            item.quantity += quantity
            item.save(
                update_fields=[
                    "quantity",
                    "updated_at",
                ]
            )

        serializer.instance = item