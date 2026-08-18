from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Order
from .serializers import OrderSerializer
from .permissions import IsOrderOwnerOrStaff

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .services import (
    InvalidOrderTransitionError,
    OrderNotFoundError,
    OrderService,
)

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)




@extend_schema_view(
    list=extend_schema(
        operation_id="order_list",
        summary="List orders",
        description=(
            "Returns orders belonging to the authenticated user. "
            "Staff users can access all orders."
        ),
        responses={
            200: OrderSerializer(many=True),
        },
    ),

    retrieve=extend_schema(
        operation_id="order_retrieve",
        summary="Retrieve order",
        description=(
            "Returns a specific order. "
            "Customers can access their own orders, while staff "
            "users can access any order."
        ),
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                required=True,
                description="Order ID.",
            ),
        ],
        responses={
            200: OrderSerializer,
            404: OpenApiResponse(
                description="Order not found."
            ),
        },
    ),

    change_status=extend_schema(
        operation_id="order_change_status",
        summary="Change order status",
        description=(
            "Changes the status of an order according to the "
            "allowed order state transitions. Customers can only "
            "cancel their own orders. Staff users can perform "
            "other allowed status transitions."
        ),
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                required=True,
                description="Order ID.",
            ),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "New order status.",
                    },
                },
                "required": ["status"],
            }
        },
        responses={
            200: OrderSerializer,

            400: OpenApiResponse(
                description=(
                    "Status is missing or the requested "
                    "status transition is invalid."
                )
            ),

            403: OpenApiResponse(
                description=(
                    "Customer attempted a status change "
                    "other than cancellation."
                )
            ),

            404: OpenApiResponse(
                description="Order not found."
            ),
        },
    ),
)

class OrderViewSet(ReadOnlyModelViewSet):

    serializer_class = OrderSerializer

    permission_classes = [
        IsAuthenticated,
        IsOrderOwnerOrStaff,
    ]

    queryset = Order.objects.prefetch_related(
        "items",
    ).select_related(
        "user",
    )

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.is_superuser:
            return self.queryset

        return self.queryset.filter(
            user=user
        )


    @action(
        detail=True,
        methods=["post"],
        url_path="status",
    )
    def change_status(self, request, pk=None):

        new_status = request.data.get("status")

        if not new_status:

            return Response(
                {
                    "detail": "Status is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # Get order
        # -------------------------------------------------

        try:

            order = self.get_queryset().get(
                pk=pk
            )

        except Order.DoesNotExist:

            return Response(
                {
                    "detail": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # -------------------------------------------------
        # Authorization
        # -------------------------------------------------

        if (
            not request.user.is_staff
            and new_status != Order.Status.CANCELLED
        ):

            return Response(
                {
                    "detail": (
                        "Customers can only cancel "
                        "their own orders."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # -------------------------------------------------
        # Change status
        # -------------------------------------------------

        try:

            order = OrderService.change_status(
                order_id=order.id,
                new_status=new_status,
            )

        except OrderNotFoundError:

            return Response(
                {
                    "detail": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except InvalidOrderTransitionError as exc:

            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(order)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )