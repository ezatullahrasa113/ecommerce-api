from django.db import transaction

from cart.models import Cart
from orders.models import Order, OrderItem
from products.models import Product

from .models import CheckoutRequest

class CheckoutError(Exception):
    """Base exception for checkout errors."""


class CartNotFoundError(CheckoutError):
    """Raised when the customer has no cart."""

class CheckoutValidationError(Exception):
    pass



class CheckoutService:

    @staticmethod
    def checkout(
        *,
        user,
        idempotency_key,
    ):

        # -------------------------------------------------
        # 1. Get customer's cart
        # -------------------------------------------------

        cart = Cart.objects.filter(
            user=user
        ).first()

        if not cart:
            raise CartNotFoundError(
                "Cart not found."
            )

        validation_error = None
        order = None

        with transaction.atomic():

            # -------------------------------------------------
            # 2. Lock or create CheckoutRequest
            # -------------------------------------------------

            checkout_request, created = (
                CheckoutRequest.objects
                .select_for_update()
                .get_or_create(
                    user=user,
                    idempotency_key=idempotency_key,
                    defaults={
                        "status": (
                            CheckoutRequest.Status.PROCESSING
                        )
                    },
                )
            )

            # -------------------------------------------------
            # 3. Already completed
            # -------------------------------------------------

            if (
                not created
                and checkout_request.status
                == CheckoutRequest.Status.COMPLETED
            ):
                return checkout_request.order

            # -------------------------------------------------
            # 4. Retry failed checkout
            # -------------------------------------------------

            if (
                not created
                and checkout_request.status
                == CheckoutRequest.Status.FAILED
            ):
                checkout_request.status = (
                    CheckoutRequest.Status.PROCESSING
                )

                checkout_request.order = None

                checkout_request.save(
                    update_fields=[
                        "status",
                        "order",
                        "failure_reason",
                    ]
                )

            try:

                # ---------------------------------------------
                # 5. Get cart items
                # ---------------------------------------------

                items = list(
                    cart.items.select_related("product")
                )

                if not items:
                    raise CheckoutValidationError(
                        "Your cart is empty."
                    )

                # ---------------------------------------------
                # 6. Get product IDs
                # ---------------------------------------------

                product_ids = [
                    item.product_id
                    for item in items
                ]

                # ---------------------------------------------
                # 7. Lock products
                # ---------------------------------------------

                products = (
                    Product.objects
                    .select_for_update()
                    .filter(
                        id__in=product_ids
                    )
                )

                products_by_id = {
                    product.id: product
                    for product in products
                }

                # ---------------------------------------------
                # 8. Validate products and stock
                # ---------------------------------------------

                for item in items:

                    product = products_by_id.get(
                        item.product_id
                    )

                    if product is None:
                        raise CheckoutValidationError(
                            "A product in your cart "
                            "is no longer available."
                        )

                    if not product.is_active:
                        raise CheckoutValidationError(
                            f"{product.name} "
                            "is no longer available."
                        )

                    if product.stock < item.quantity:
                        raise CheckoutValidationError(
                            f"Insufficient stock "
                            f"for {product.name}."
                        )

                # ---------------------------------------------
                # 9. Calculate total
                # ---------------------------------------------

                total_price = sum(
                    products_by_id[
                        item.product_id
                    ].price * item.quantity
                    for item in items
                )

                # ---------------------------------------------
                # 10. Create Order
                # ---------------------------------------------

                order = Order.objects.create(
                    user=user,
                    status=Order.Status.PENDING,
                    total_price=total_price,
                )

                # ---------------------------------------------
                # 11. Create OrderItems
                # ---------------------------------------------

                order_items = []

                for item in items:

                    product = products_by_id[
                        item.product_id
                    ]

                    order_items.append(
                        OrderItem(
                            order=order,
                            product=product,
                            product_name=product.name,
                            product_price=product.price,
                            quantity=item.quantity,
                        )
                    )

                OrderItem.objects.bulk_create(
                    order_items
                )

                # ---------------------------------------------
                # 12. Reduce stock
                # ---------------------------------------------

                for item in items:

                    product = products_by_id[
                        item.product_id
                    ]

                    product.stock -= item.quantity

                    product.save(
                        update_fields=["stock"]
                    )

                # ---------------------------------------------
                # 13. Clear cart
                # ---------------------------------------------

                cart.items.all().delete()

                # ---------------------------------------------
                # 14. Complete CheckoutRequest
                # ---------------------------------------------

                checkout_request.status = (
                    CheckoutRequest.Status.COMPLETED
                )
                checkout_request.failure_reason = None
                checkout_request.order = order

                checkout_request.save(
                    update_fields=[
                        "status",
                        "order",
                         "failure_reason",
                    ]
                )

            except CheckoutValidationError as exc:

                # ---------------------------------------------
                # Expected checkout failure
                # ---------------------------------------------

                checkout_request.status = (
                    CheckoutRequest.Status.FAILED
                )

                checkout_request.order = None

                checkout_request.failure_reason = str(exc)

                checkout_request.save(
                    update_fields=[
                        "status",
                        "order",
                        "failure_reason",
                    ]
                )

                validation_error = exc

        # -------------------------------------------------
        # 15. Raise AFTER transaction commits
        # -------------------------------------------------

        if validation_error:
            raise validation_error

        return order