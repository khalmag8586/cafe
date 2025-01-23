from django.http import JsonResponse

from django.utils.translation import gettext_lazy as _


class CustomErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, Exception):
            response_data = {
                "error": "Internal Server Error",
                "status_code": 500,
                "message": str(
                    _(
                        "An internal server error occurred. Please contact with Administrator"
                    )
                ),
            }

            return JsonResponse(response_data, status=500)
