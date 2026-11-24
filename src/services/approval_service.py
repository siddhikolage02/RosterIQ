
from datetime import datetime

from sqlalchemy.orm import Session

from src.database.models import (
    Employee,
    RosterRun,
    RosterApproval,
)

from src.scheduling.validation_service import validate_roster
from src.services.audit_service import log_roster_change


def _get_employee(db: Session, employee_id: int):
    employee = db.query(Employee).filter(
        Employee.id == employee_id
    ).first()

    if not employee or employee.employment_status != "Active":
        raise ValueError("Active employee account not found.")

    return employee


def submit_roster_for_approval(
    db: Session,
    roster_id: int,
    submitted_by_employee_id: int,
):
    """Submit a valid draft roster for Manager approval."""

    employee = _get_employee(db, submitted_by_employee_id)

    if employee.role not in ["Manager", "Pod Lead"]:
        raise PermissionError("Only Managers and Pod Leads can submit rosters.")

    roster = db.query(RosterRun).filter(
        RosterRun.id == roster_id
    ).first()

    if not roster:
        raise ValueError("Roster not found.")

    if roster.status != "Draft":
        raise ValueError("Only draft rosters can be submitted.")

    validation = validate_roster(db, roster_id)

    if not validation["is_valid"]:
        raise ValueError(
            "Roster has conflicts or coverage gaps. "
            "Resolve them before submitting."
        )

    if validation["total_entries"] == 0:
        raise ValueError("An empty roster cannot be submitted.")

    approval = RosterApproval(
        roster_id=roster_id,
        submitted_by_employee_id=submitted_by_employee_id,
        status="Pending",
    )

    try:
        db.add(approval)
        roster.status = "Pending Approval"

        log_roster_change(
            db,
            roster_id=roster_id,
            changed_by_employee_id=submitted_by_employee_id,
            action="Submitted for Approval",
            new_values={"status": "Pending Approval"},
        )

        db.commit()
        db.refresh(approval)
        return approval

    except Exception:
        db.rollback()
        raise


def get_pending_approvals(db: Session):
    """Get all pending roster approval requests."""

    return (
        db.query(RosterApproval)
        .filter(RosterApproval.status == "Pending")
        .order_by(RosterApproval.submitted_at)
        .all()
    )


def approve_roster(
    db: Session,
    approval_id: int,
    reviewed_by_employee_id: int,
    comments: str = None,
):
    """Approve a submitted roster. Only a different Manager may approve."""

    reviewer = _get_employee(db, reviewed_by_employee_id)

    if reviewer.role != "Manager":
        raise PermissionError("Only a Manager can approve a roster.")

    approval = db.query(RosterApproval).filter(
        RosterApproval.id == approval_id
    ).first()

    if not approval or approval.status != "Pending":
        raise ValueError("Pending approval request not found.")

    if approval.submitted_by_employee_id == reviewed_by_employee_id:
        raise PermissionError("The submitter cannot approve their own roster.")

    roster = db.query(RosterRun).filter(
        RosterRun.id == approval.roster_id
    ).first()

    if not roster or roster.status != "Pending Approval":
        raise ValueError("Roster is not awaiting approval.")

    validation = validate_roster(db, roster.id)

    if not validation["is_valid"]:
        raise ValueError("Roster is no longer valid and cannot be approved.")

    try:
        approval.status = "Approved"
        approval.reviewed_by_employee_id = reviewed_by_employee_id
        approval.comments = comments
        approval.reviewed_at = datetime.utcnow()

        roster.status = "Approved"

        log_roster_change(
            db,
            roster_id=roster.id,
            changed_by_employee_id=reviewed_by_employee_id,
            action="Roster Approved",
            new_values={"status": "Approved"},
            comments=comments,
        )

        db.commit()
        db.refresh(approval)
        return approval

    except Exception:
        db.rollback()
        raise


def reject_roster(
    db: Session,
    approval_id: int,
    reviewed_by_employee_id: int,
    comments: str,
):
    """Reject a roster and return it to Draft for corrections."""

    reviewer = _get_employee(db, reviewed_by_employee_id)

    if reviewer.role != "Manager":
        raise PermissionError("Only a Manager can reject a roster.")

    if not comments or not comments.strip():
        raise ValueError("Rejection comments are required.")

    approval = db.query(RosterApproval).filter(
        RosterApproval.id == approval_id
    ).first()

    if not approval or approval.status != "Pending":
        raise ValueError("Pending approval request not found.")

    if approval.submitted_by_employee_id == reviewed_by_employee_id:
        raise PermissionError("The submitter cannot reject their own roster.")

    roster = db.query(RosterRun).filter(
        RosterRun.id == approval.roster_id
    ).first()

    if not roster or roster.status != "Pending Approval":
        raise ValueError("Roster is not awaiting approval.")

    try:
        approval.status = "Rejected"
        approval.reviewed_by_employee_id = reviewed_by_employee_id
        approval.comments = comments
        approval.reviewed_at = datetime.utcnow()

        roster.status = "Draft"

        log_roster_change(
            db,
            roster_id=roster.id,
            changed_by_employee_id=reviewed_by_employee_id,
            action="Roster Rejected",
            old_values={"status": "Pending Approval"},
            new_values={"status": "Draft"},
            comments=comments,
        )

        db.commit()
        db.refresh(approval)
        return approval

    except Exception:
        db.rollback()
        raise


def publish_approved_roster(
    db: Session,
    roster_id: int,
    published_by_employee_id: int,
):
    """Publish an approved roster. Only a Manager may publish."""

    publisher = _get_employee(db, published_by_employee_id)

    if publisher.role != "Manager":
        raise PermissionError("Only a Manager can publish a roster.")

    roster = db.query(RosterRun).filter(
        RosterRun.id == roster_id
    ).first()

    if not roster:
        raise ValueError("Roster not found.")

    if roster.status != "Approved":
        raise ValueError("Only approved rosters can be published.")

    validation = validate_roster(db, roster_id)

    if not validation["is_valid"]:
        raise ValueError("Roster validation failed. Publication blocked.")

    approved_record = db.query(RosterApproval).filter(
        RosterApproval.roster_id == roster_id,
        RosterApproval.status == "Approved",
    ).order_by(RosterApproval.reviewed_at.desc()).first()

    if not approved_record:
        raise ValueError("No approved record exists for this roster.")

    try:
        roster.status = "Published"

        log_roster_change(
            db,
            roster_id=roster_id,
            changed_by_employee_id=published_by_employee_id,
            action="Roster Published",
            old_values={"status": "Approved"},
            new_values={"status": "Published"},
        )

        db.commit()
        db.refresh(roster)
        return roster

    except Exception:
        db.rollback()
        raise
