

class PaymentProviderError(Exception):
    """Base exception for payment provider errors."""

class MockPaymentProvider:

    @staticmethod
    def verify(*, transaction_id, amount):
        """
        Mock payment verification.

        In production, this method will communicate
        with the real payment gateway.
        """

        if not transaction_id:
            raise PaymentProviderError(
                "Transaction ID is required."
            )

        if transaction_id.startswith("fail-"):
            raise PaymentProviderError(
                "Payment verification failed."
            )

        return {
            "success": True,
            "transaction_id": transaction_id,
            "amount": amount,
        }