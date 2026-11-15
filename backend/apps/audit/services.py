from .activity import mark_explicit_audit_record
from .models import AuditRecord


def record_audit_event(
    *,
    domain,
    action,
    actor,
    application=None,
    membership=None,
    target_type="",
    target_id=None,
    operation="",
    request_method="",
    request_path="",
    previous_state=None,
    new_state=None,
    reason="",
) -> AuditRecord:
    record = AuditRecord.objects.create(
        domain=domain,
        action=action,
        actor=actor,
        application=application,
        membership=membership,
        target_type=target_type,
        target_id=target_id,
        operation=operation,
        request_method=request_method,
        request_path=request_path,
        previous_state=previous_state or {},
        new_state=new_state or {},
        reason=reason,
    )
    mark_explicit_audit_record()
    return record
