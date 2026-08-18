from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from .permissions import IsCartItemOwnerOrStaff,IsCartOwnerOrStaff
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view
)

class MyCartView(generics.RetrieveAPIView):

    serializer_class = CartSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    @extend_schema(
            operation_id="my_cart_retrieve",
            summary="Retrieve my cart",
            description=(
                "Returns the authenticated user's shopping cart. "
                "If the user does not have a cart yet, a new empty "
                "cart is created automatically."
            ),
            responses={
                200: CartSerializer,
            },
        )
    def get(self, request, *args, **kwargs):
            return super().get(request, *args, **kwargs)

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

    @extend_schema(
        operation_id="cart_detail_retrieve",
        summary="Retrieve cart by ID",
        description=(
            "Returns a specific shopping cart by its ID. "
            "Users can access their own cart, while staff users "
            "can access other carts."
        ),
        responses={
            200: CartSerializer,
            404: OpenApiResponse(
                description="Cart not found."
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)



@extend_schema_view(
    list=extend_schema(
        summary="List cart items",
        description=(
            "Returns the authenticated user's cart items. "
            "Staff users can access cart items from all users."
        ),
        responses={
            200: CartItemSerializer(many=True),
        },
    ),

    retrieve=extend_schema(
        summary="Retrieve cart item",
        description="Returns a specific cart item.",
        responses={
            200: CartItemSerializer,
            404: OpenApiResponse(
                description="Cart item not found."
            ),
        },
    ),

    create=extend_schema(
        summary="Add product to cart",
        description=(
            "Adds a product to the authenticated user's cart. "
            "If the product already exists in the cart, its "
            "quantity is increased instead of creating a duplicate item."
        ),
        request=CartItemSerializer,
        responses={
            201: CartItemSerializer,
            400: OpenApiResponse(
                description="Invalid product or quantity."
            ),
        },
    ),

    update=extend_schema(
        summary="Update cart item",
        description="Replaces the quantity of an existing cart item.",
        request=CartItemSerializer,
        responses={
            200: CartItemSerializer,
            400: OpenApiResponse(
                description="Invalid cart item data."
            ),
            404: OpenApiResponse(
                description="Cart item not found."
            ),
        },
    ),

    partial_update=extend_schema(
        summary="Partially update cart item",
        description=(
            "Partially updates an existing cart item."
        ),
        request=CartItemSerializer,
        responses={
            200: CartItemSerializer,
            400: OpenApiResponse(
                description="Invalid cart item data."
            ),
            404: OpenApiResponse(
                description="Cart item not found."
            ),
        },
    ),

    destroy=extend_schema(
        summary="Remove cart item",
        description=(
            "Removes a product from the authenticated user's cart."
        ),
        responses={
            204: OpenApiResponse(
                description="Cart item removed successfully."
            ),
            404: OpenApiResponse(
                description="Cart item not found."
            ),
        },
    ),
)

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