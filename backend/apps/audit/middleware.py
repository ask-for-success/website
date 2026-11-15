from uuid import UUID

from django.db import transaction

from .activity import (
    begin_request_audit,
    end_request_audit,
    explicit_audit_record_created,
)
from .models import AuditAction, AuditDomain
from .services import record_audit_event


MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
DOMAIN_BY_APP_NAME = {
    "accounts": AuditDomain.ACCOUNTS,
    "access_control": AuditDomain.ACCESS_CONTROL,
    "organization": AuditDomain.ORGANIZATION,
    "content": AuditDomain.CONTENT,
    "events": AuditDomain.EVENTS,
    "recruitment": AuditDomain.RECRUITMENT,
    "memberships": AuditDomain.MEMBERSHIP,
}


def _get_response_data(response):
    data = getattr(response, "data", None)
    return data if isinstance(data, dict) else {}


def _parse_uuid(value):
    if not value:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


class ActivityAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _should_wrap(request) -> bool:
        return bool(
            request.method in MUTATING_METHODS
            and request.path.startswith("/api/v1/")
            and not request.path.startswith("/api/v1/audit/")
        )

    @staticmethod
    def _action_for(request, response):
        if request.method == "DELETE":
            return AuditAction.API_DELETED
        if request.method in {"PUT", "PATCH"}:
            return AuditAction.API_UPDATED
        if response.status_code == 201:
            return AuditAction.API_CREATED
        return AuditAction.API_ACTION_PERFORMED

    @staticmethod
    def _target_id(request, response):
        response_id = _parse_uuid(_get_response_data(response).get("id"))
        if response_id:
            return response_id
        resolver_match = request.resolver_match
        if not resolver_match:
            return None
        for key, value in reversed(tuple(resolver_match.kwargs.items())):
            if key.endswith("_id"):
                parsed = _parse_uuid(value)
                if parsed:
                    return parsed
        return None

    def _record_activity(self, request, response) -> None:
        user = getattr(request, "user", None)
        resolver_match = request.resolver_match
        if not user or not user.is_authenticated or not resolver_match:
            return
        app_name = resolver_match.app_name or ""
        domain = DOMAIN_BY_APP_NAME.get(app_name, AuditDomain.ACCOUNTS)
        operation = resolver_match.view_name or resolver_match.url_name or ""
        record_audit_event(
            domain=domain,
            action=self._action_for(request, response),
            actor=user,
            target_type=operation or app_name or "api",
            target_id=self._target_id(request, response),
            operation=operation,
            request_method=request.method,
            request_path=request.path,
        )

    def __call__(self, request):
        if not self._should_wrap(request):
            return self.get_response(request)

        token = begin_request_audit()
        try:
            with transaction.atomic():
                response = self.get_response(request)
                if (
                    200 <= response.status_code < 400
                    and not explicit_audit_record_created()
                ):
                    self._record_activity(request, response)
                return response
        finally:
            end_request_audit(token)
