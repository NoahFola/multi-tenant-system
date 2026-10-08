import pytest
from common.errors import ConflictError
from app.domain.state_machine import assert_transition

def test_submitted_to_manager_review():
    assert_transition("SUBMITTED", "MANAGER_REVIEW")

def test_manager_review_to_approved():
    assert_transition("MANAGER_REVIEW", "APPROVED")

def test_manager_review_to_rejected():
    assert_transition("MANAGER_REVIEW", "REJECTED")

def test_submitted_to_approved_blocked():
    with pytest.raises(ConflictError) as exc:
        assert_transition("SUBMITTED", "APPROVED")
    assert "Cannot move from SUBMITTED to APPROVED" in str(exc.value)

def test_submitted_to_rejected_blocked():
    with pytest.raises(ConflictError):
        assert_transition("SUBMITTED", "REJECTED")

def test_approved_is_terminal():
    with pytest.raises(ConflictError):
        assert_transition("APPROVED", "MANAGER_REVIEW")

def test_rejected_is_terminal():
    with pytest.raises(ConflictError):
        assert_transition("REJECTED", "APPROVED")

def test_unknown_from_status():
    with pytest.raises(ConflictError):
        assert_transition("DRAFT", "SUBMITTED")

def test_empty_from_status():
    with pytest.raises(ConflictError):
        assert_transition("", "SUBMITTED")
