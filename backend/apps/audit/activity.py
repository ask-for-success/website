from contextvars import ContextVar, Token


_request_audit_state = ContextVar("request_audit_state", default=None)


def begin_request_audit() -> Token:
    return _request_audit_state.set({"explicit_record_created": False})


def mark_explicit_audit_record() -> None:
    state = _request_audit_state.get()
    if state is not None:
        state["explicit_record_created"] = True


def explicit_audit_record_created() -> bool:
    state = _request_audit_state.get()
    return bool(state and state["explicit_record_created"])


def end_request_audit(token: Token) -> None:
    _request_audit_state.reset(token)
