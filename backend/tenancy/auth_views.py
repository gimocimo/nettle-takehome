from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView


def me_payload(user):
    memberships = user.memberships.select_related("organization").order_by("organization__name")
    return {
        "user": {"id": user.id, "email": user.email, "name": user.get_full_name() or user.email},
        "memberships": [
            {
                "role": membership.role,
                "organization": {
                    "slug": membership.organization.slug,
                    "name": membership.organization.name,
                    "language": membership.organization.language,
                    "currency": membership.organization.currency,
                },
            }
            for membership in memberships
        ],
    }


def enforce_csrf(request):
    """DRF only checks CSRF for already-authenticated sessions. Login needs it too,
    otherwise a malicious site can log the victim into the attacker's account."""
    check = CSRFCheck(lambda _request: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise PermissionDenied(f"CSRF failed: {reason}")


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        enforce_csrf(request._request)
        email = str(request.data.get("email", "")).strip().lower()
        password = str(request.data.get("password", ""))
        user = authenticate(request._request, username=email, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST
            )
        login(request._request, user)
        return Response(me_payload(user))


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(me_payload(request.user))
