import base64
import hashlib
from datetime import date
from user_agents import parse as parse_user_agent

from django.http import HttpResponse
from django.contrib.auth import authenticate
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.shared.utils.redis_utils import redis_connection, get_redis_connection
from apps.shared.utils.logging import logger
from apps.shared.utils.utils import get_user_hash


redis_connection = get_redis_connection()


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


class VisitorCounterMiddleware(MiddlewareMixin):
    """
    Middleware to track unique visitors using Redis HyperLogLog.
    - Authenticated users: user_id + user_agent
    - Anonymous users: IP address + user_agent

    Skips tracking for bots and specific excluded paths.

    NOTE: HLL keys expire after 10 days.
    """
    EXCLUDE_PATHS = ['/health-check/', '/favicon.ico']

    def process_request(self, request):
        if settings.IS_LOCAL:
            return  # Skips in local environment

        user_agent = request.META.get('HTTP_USER_AGENT', '')
        path = request.path
        if any(path.startswith(p) for p in self.EXCLUDE_PATHS):
            return  # Skips excluded paths

        user_hash, message = get_user_hash(request)
        if user_hash is None:
            return

        # Decodes JWT Token manually, because AuthenticationMiddleware only handles session-based authentication
        if not request.user.is_authenticated:
            jwt_auth = JWTAuthentication()
            try:
                user, token = jwt_auth.authenticate(request)
                request.user = user
            except Exception:
                pass  # Keeps AnonymousUser if authentication fails

        today_str = date.today().strftime('%Y-%m-%d')
        logger.info(f"Processing unique visitor for {today_str}")

        # --- 1️⃣ Tracks unique visitors (all users) ---
        visitor_hll_key = f"unique_visitors:{today_str}"
        try:
            redis_connection.pfadd(visitor_hll_key, user_hash)
        except Exception as e:
            logger.error(f"Unique Visitor Middleware | Redis error (visitor HLL): {e}")
        finally:
            redis_connection.expire(visitor_hll_key, 60 * 60 * 24 * 10) # Expire in 10 days

        # --- 2️⃣ Tracks unique authenticated users ---
        if request.user.is_authenticated:
            auth_base = f"user:{request.user.id}:{user_agent}"
            auth_hash = hashlib.sha256(auth_base.encode('utf-8')).hexdigest()
            auth_hll_key = f"unique_auth_users:{today_str}"
            try:
                redis_connection.pfadd(auth_hll_key, auth_hash)
            except Exception as e:
                logger.error(f"Unique Visitor Middleware | Redis error (auth user HLL): {e}")
            finally:
                redis_connection.expire(auth_hll_key, 60 * 60 * 24 * 10)  # Expire in 10 days
