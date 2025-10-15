import base64
from django.http import HttpResponse
from django.contrib.auth import authenticate


class AdminBasicAuthMiddleware:
    """
    Middleware to enforce Basic Authentication for accessing the Django admin interface.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            if 'HTTP_AUTHORIZATION' in request.META:
                auth = request.META['HTTP_AUTHORIZATION'].split()
                if len(auth) == 2 and auth[0].lower() == 'basic':
                    username, password = base64.b64decode(auth[1]).decode('utf-8').split(':', 1)
                    user = authenticate(username=username, password=password)
                    if user and user.user_role in ['admin', 'super_admin']:
                        request.user = user
                        return self.get_response(request)
            response = HttpResponse(status=401)
            response['WWW-Authenticate'] = 'Basic realm="Admin Access"'
            return response
        return self.get_response(request)
