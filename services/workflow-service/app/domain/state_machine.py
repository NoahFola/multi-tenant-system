from common.errors import ConflictError

# Legal transitions: from_status → set of allowed to_statuses
TRANSITIONS: dict[str, set[str]] = {
    "SUBMITTED":      {"MANAGER_REVIEW"},
    "MANAGER_REVIEW": {"APPROVED", "REJECTED"},
}

def assert_transition(from_status: str, to_status: str) -> None:
    """Raises ConflictError if the move is not in the table."""
    allowed = TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise ConflictError(
            f"Cannot move from {from_status} to {to_status}"
        )
