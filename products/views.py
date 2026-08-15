from rest_framework.viewsets import ModelViewSet
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter,OrderingFilter
from .pagination import ProductPagination 
from accounts.permissions import ReadOnlyOrStaff

class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    permission_classes =[ReadOnlyOrStaff]


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.select_related('category')
    serializer_class = ProductSerializer
    pagination_class = ProductPagination
    lookup_field = 'slug'
    permission_classes =[ReadOnlyOrStaff]


    filter_backends = [
    DjangoFilterBackend,
    SearchFilter,
    OrderingFilter,
    ]

    filterset_fields = [
        'category',
        'is_active'
    ]

    search_fields = [
        'name',
        'description'
    ]

    ordering_fields = [
        'price',
        'created_at'
    ]

    ordering = ['-created_at']

