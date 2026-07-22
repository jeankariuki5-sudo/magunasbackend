from django.http import JsonResponse
from django_ratelimit.exceptions import Ratelimited


def Handler403(request, exception = None):
    # NEW: Return 429 for rate limit, 403 for everything else
    if isinstance(exception, Ratelimited):
        return JsonResponse({
            'error': 'Too many requests. Please slow down and try again shortly.'
        }, status = 429)

    return JsonResponse({
        'error': 'Permission denied.'
    }, status = 403)