from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Order
from .serializers import OrderSerializer
from .permissions import IsOrderOwnerOrStaff


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