def emit_audit_event(
    db,
    tenant_id: str,
    actor_id: str,
    action: str,          # e.g. "user.invited", "user.role_changed", "user.disabled"
    resource_type: str,   # e.g. "user", "invitation"
    resource_id: str,
    metadata: dict,
    ip: str = "",
) -> None:
    """STUB: will write to AUDIT_LOGS in Step 6. Currently a no-op."""
    pass
