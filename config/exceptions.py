from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return None

    if isinstance(response.data, dict):
        if "detail" in response.data:
            response.data = {
                "error": {
                    "detail": response.data["detail"],
                }
            }

        else:
            response.data = {
                "error": {
                    "detail": "Validation error.",
                    "fields": response.data,
                }
            }

    return response