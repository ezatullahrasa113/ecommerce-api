from rest_framework.viewsets import ModelViewSet
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter,OrderingFilter
from .pagination import ProductPagination 
from accounts.permissions import ReadOnlyOrStaff

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)


@extend_schema_view(
    list=extend_schema(
        summary="List categories",
        description="Returns all product categories.",
        responses={
            200: CategorySerializer(many=True),
        },
    ),

    retrieve=extend_schema(
        summary="Retrieve category",
        description=(
            "Returns a category using its unique slug."
        ),
        parameters=[
            OpenApiParameter(
                name="slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique category slug.",
            ),
        ],
        responses={
            200: CategorySerializer,
            404: OpenApiResponse(
                description="Category not found."
            ),
        },
    ),

    create=extend_schema(
        summary="Create category",
        description=(
            "Creates a new product category. "
            "The slug is generated automatically."
        ),
        request=CategorySerializer,
        responses={
            201: CategorySerializer,
            400: OpenApiResponse(
                description="Invalid category data."
            ),
        },
    ),

    update=extend_schema(
        summary="Update category",
        description="Replaces an existing category.",
        request=CategorySerializer,
        responses={
            200: CategorySerializer,
            400: OpenApiResponse(
                description="Invalid category data."
            ),
            404: OpenApiResponse(
                description="Category not found."
            ),
        },
    ),

    partial_update=extend_schema(
        summary="Partially update category",
        description="Partially updates an existing category.",
        request=CategorySerializer,
        responses={
            200: CategorySerializer,
            400: OpenApiResponse(
                description="Invalid category data."
            ),
            404: OpenApiResponse(
                description="Category not found."
            ),
        },
    ),

    destroy=extend_schema(
        summary="Delete category",
        description="Deletes an existing category.",
        responses={
            204: OpenApiResponse(
                description="Category deleted successfully."
            ),
            404: OpenApiResponse(
                description="Category not found."
            ),
        },
    ),
)

class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    permission_classes =[ReadOnlyOrStaff]


@extend_schema_view(
    list=extend_schema(
        summary="List products",
        description=(
            "Returns a paginated list of products. "
            "Products can be filtered by category and active status, "
            "searched by name or description, and ordered by price "
            "or creation date."
        ),
        parameters=[
            OpenApiParameter(
                name="category",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter products by category ID.",
            ),
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter products by active status.",
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Search products by name or description."
                ),
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Order by price or created_at. "
                    "Prefix with '-' for descending order."
                ),
            ),
        ],
        responses={
            200: ProductSerializer(many=True),
        },
    ),

    retrieve=extend_schema(
        summary="Retrieve product",
        description=(
            "Returns a product using its unique slug."
        ),
        parameters=[
            OpenApiParameter(
                name="slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique product slug.",
            ),
        ],
        responses={
            200: ProductSerializer,
            404: OpenApiResponse(
                description="Product not found."
            ),
        },
    ),

    create=extend_schema(
        summary="Create product",
        description=(
            "Creates a new product. "
            "The category is selected using category_id "
            "and the slug is generated automatically."
        ),
        request=ProductSerializer,
        responses={
            201: ProductSerializer,
            400: OpenApiResponse(
                description="Invalid product data."
            ),
        },
    ),

    update=extend_schema(
        summary="Update product",
        description="Replaces an existing product.",
        request=ProductSerializer,
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(
                description="Invalid product data."
            ),
            404: OpenApiResponse(
                description="Product not found."
            ),
        },
    ),

    partial_update=extend_schema(
        summary="Partially update product",
        description="Partially updates an existing product.",
        request=ProductSerializer,
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(
                description="Invalid product data."
            ),
            404: OpenApiResponse(
                description="Product not found."
            ),
        },
    ),

    destroy=extend_schema(
        summary="Delete product",
        description="Deletes an existing product.",
        responses={
            204: OpenApiResponse(
                description="Product deleted successfully."
            ),
            404: OpenApiResponse(
                description="Product not found."
            ),
        },
    ),
)

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

