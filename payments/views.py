from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
)

from .models import Payment
from .services import (
PaymentError,
PaymentService,
)

from .serializers import (
    PaymentSerializer,
    PaymentCreateSerializer,
    PaymentVerifySerializer,
)


from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)



class PaymentViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = PaymentSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        if getattr(
            self,
            "swagger_fake_view",
            False,
        ):
            return Payment.objects.none()

        return (
            Payment.objects
            .filter(
                user=self.request.user
            )
            .select_related("order")
        )

    # =====================================================
    # Create payment
    # =====================================================
    
    @extend_schema(
        summary="Create payment",
        description=(
            "Creates a pending payment for the authenticated "
            "user's order."
        ),
        request=PaymentCreateSerializer,
        responses={
            201: PaymentSerializer,
            400: OpenApiResponse(
                description="Payment creation failed."
            ),
        },
    )

    @action(
        detail=False,
        methods=["post"],
        url_path=r"(?P<order_id>\d+)/create",
    )
    def create_payment(
        self,
        request,
        order_id=None,
    ):

        payment_method = request.data.get(
            "payment_method"
        )

        try:

            payment = PaymentService.create_payment(
                user=request.user,
                order_id=order_id,
                payment_method=payment_method,
            )

        except PaymentError as exc:

            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(
            payment
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    # =====================================================
    # Verify payment
    # =====================================================

    @extend_schema(
        summary="Verify payment",
        description=(
            "Verifies a pending payment with the payment "
            "provider. If verification succeeds, the payment "
            "is marked as succeeded and the order is confirmed."
        ),
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                required=True,
                description="ID of the payment.",
            ),
        ],
        request=PaymentVerifySerializer,
        responses={
            200: PaymentSerializer,
            400: OpenApiResponse(
                description="Payment verification failed."
            ),
            404: OpenApiResponse(
                description="Payment not found.",
            ),
        },
    )

    @action(
        detail=True,
        methods=["post"],
        url_path="verify",
    )

    def verify_payment(
        self,
        request,
        pk=None,
    ):

        transaction_id = request.data.get(
            "transaction_id"
        )

        try:
            payment = Payment.objects.get(
                id=pk,
                user=request.user,
            )

        except Payment.DoesNotExist:
            return Response(
                {
                    "detail": "Payment not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            payment = PaymentService.complete_payment(
                payment_id=payment.id,
                transaction_id=transaction_id,
            )

        except PaymentError as exc:
            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(payment)

        return Response(
            serializer.data,
            status = status.HTTP_200_OK,
        )