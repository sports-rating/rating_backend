import base64
import hashlib
from datetime import date
from user_agents import parse as parse_user_agent

from django.http import HttpResponse
from django.contrib.auth import authenticate
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.shared.utils.redis_utils import redis_connection, get_redis_connection
from apps.shared.utils.logging import logger


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


class UniqueVisitorMiddleware(MiddlewareMixin):
    """
    Middleware to track unique visitors using Redis HyperLogLog.
    - Authenticated users: user_id + user_agent
    - Anonymous users: IP address + user_agent
    """
    EXCLUDE_PATHS = ['/health-check/', '/favicon.ico']

    def process_request(self, request):
        path = request.path
        if any(path.startswith(p) for p in self.EXCLUDE_PATHS):
            return  # Skip excluded paths

        user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent_parsed = parse_user_agent(user_agent)
        if user_agent_parsed.is_bot:
            return  # Ignore bots

        # Decode JWT Token manually, because AuthenticationMiddleware only handles session-based authentication
        jwt_auth = JWTAuthentication()
        try:
            user, token = jwt_auth.authenticate(request)
            request.user = user
        except Exception:
            request.user = AnonymousUser()

        today_str = date.today().strftime('%Y-%m-%d')
        logger.info(f"Processing unique visitor for {today_str}")

        # --- 1️⃣ Track unique visitors (all users) ---
        visitor_base = f"{ip}:{user_agent}"
        visitor_hash = hashlib.sha256(visitor_base.encode('utf-8')).hexdigest()
        visitor_hll_key = f"unique_visitors:{today_str}"
        try:
            redis_connection.pfadd(visitor_hll_key, visitor_hash)
            logger.info(f"Counting visitor: {ip} | {user_agent} | Authenticated: {request.user.is_authenticated}")
        except Exception as e:
            logger.error(f"Unique Visitor Middleware | Redis error (visitor HLL): {e}")

        # --- 2️⃣ Track unique authenticated users ---
        if request.user.is_authenticated:
            auth_base = f"user:{request.user.id}:{user_agent}"
            auth_hash = hashlib.sha256(auth_base.encode('utf-8')).hexdigest()
            auth_hll_key = f"unique_auth_users:{today_str}"
            try:
                redis_connection.pfadd(auth_hll_key, auth_hash)
                logger.info(f"Counting authenticated user: {request.user.id} | {request.user.username} | {user_agent}")
            except Exception as e:
                logger.error(f"Unique Visitor Middleware | Redis error (auth user HLL): {e}")
