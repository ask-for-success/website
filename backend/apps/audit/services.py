from .models import AuditRecord


def record_audit_event(
    *,
    domain,
    action,
    actor,
    application=None,
    membership=None,
    previous_state=None,
    new_state=None,
    reason="",
) -> AuditRecord:
    return AuditRecord.objects.create(
        domain=domain,
        action=action,
        actor=actor,
        application=application,
        membership=membership,
        previous_state=previous_state or {},
        new_state=new_state or {},
        reason=reason,
    )
