from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)

from .services import (
    CheckoutService,
    CheckoutValidationError,
    CartNotFoundError
)

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)

@extend_schema(
    summary="Checkout cart",
    description=(
        "Creates an order from the authenticated user's cart. "
        "The Idempotency-Key header prevents duplicate checkout "
        "requests from creating multiple orders."
    ),
    parameters=[
        OpenApiParameter(
            name="Idempotency-Key",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description=(
                "Unique key used to safely retry the checkout "
                "request without creating a duplicate order."
            ),
        ),
    ],
    request=None,
    responses={
        201: OpenApiResponse(
            description="Checkout completed successfully."
        ),
        400: OpenApiResponse(
            description="Checkout validation failed."
        ),
        404: OpenApiResponse(
            description="Cart not found."
        ),
    },
)

class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        # -------------------------------------------------
        # 1. Get Idempotency-Key
        # -------------------------------------------------

        idempotency_key = request.headers.get(
            "Idempotency-Key"
        )

        if not idempotency_key:
            return Response(
                {
                    "detail": (
                        "Idempotency-Key header is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # 2. Execute checkout
        # -------------------------------------------------

        try:

            order = CheckoutService.checkout(
                user=request.user,
                idempotency_key=idempotency_key,
            )

        except CartNotFoundError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except CheckoutValidationError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # 3. Return successful response
        # -------------------------------------------------

        return Response(
            {
                "order_id": order.id,
                "total_price": str(
                    order.total_price
                ),
            },
            status=status.HTTP_201_CREATED,
        )