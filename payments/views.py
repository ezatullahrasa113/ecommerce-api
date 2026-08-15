from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Payment
from .serializers import PaymentSerializer
from .services import (
PaymentError,
PaymentService,
)

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = PaymentSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

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