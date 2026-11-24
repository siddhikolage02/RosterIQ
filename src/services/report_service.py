
from datetime import date

import pandas as pd
from sqlalchemy import text

from src.database.connection import engine


def _read_report(query: str, params: dict | None = None) -> pd.DataFrame:
    """Execute a read-only report query and return a DataFrame."""
    with engine.connect() as connection:
        result = connection.execute(text(query), params or {})
        rows = result.fetchall()
        return pd.DataFrame(rows, columns=result.keys())


def get_workforce_report(
    employment_status: str = "All",
    pod_id: int | None = None,
) -> pd.DataFrame:
    query = """
        SELECT
            e.id AS "Employee ID",
            e.employee_code AS "Employee Code",
            e.full_name AS "Employee",
            e.email AS "Email",
            e.role AS "Role",
            e.employment_status AS "Employment Status",
            COALESCE(p.name, 'Unassigned') AS "Pod",
            e.date_joined AS "Date Joined",
            e.weekly_off_day AS "Weekly Off"
        FROM employees e
        LEFT JOIN pods p ON p.id = e.pod_id
        WHERE 1 = 1
    """
    params = {}

    if employment_status != "All":
        query += " AND e.employment_status = :employment_status"
        params["employment_status"] = employment_status

    if pod_id is not None:
        query += " AND e.pod_id = :pod_id"
        params["pod_id"] = pod_id

    query += " ORDER BY e.full_name"
    return _read_report(query, params)


def get_pod_summary_report() -> pd.DataFrame:
    query = """
        SELECT
            COALESCE(p.name, 'Unassigned') AS "Pod",
            COUNT(e.id) AS "Total Employees",
            SUM(
                CASE WHEN e.employment_status = 'Active' THEN 1 ELSE 0 END
            ) AS "Active Employees",
            SUM(
                CASE WHEN e.employment_status != 'Active' THEN 1 ELSE 0 END
            ) AS "Inactive Employees"
        FROM employees e
        LEFT JOIN pods p ON p.id = e.pod_id
        GROUP BY COALESCE(p.name, 'Unassigned')
        ORDER BY "Total Employees" DESC
    """
    return _read_report(query)


def get_process_staffing_report(as_of_date: date | None = None) -> pd.DataFrame:
    target_date = as_of_date or date.today()

    query = """
        SELECT
            b.name AS "Brand",
            p.name AS "Process",
            p.minimum_staff AS "Minimum Staff",
            COUNT(DISTINCT a.employee_id) AS "Assigned Employees",
            CASE
                WHEN COUNT(DISTINCT a.employee_id) < p.minimum_staff
                THEN 'Understaffed'
                ELSE 'Covered'
            END AS "Staffing Status"
        FROM processes p
        JOIN brands b ON b.id = p.brand_id
        LEFT JOIN assignments a
            ON a.process_id = p.id
            AND a.assignment_status = 'Active'
            AND a.start_date <= :target_date
            AND (a.end_date IS NULL OR a.end_date >= :target_date)
        LEFT JOIN employees e
            ON e.id = a.employee_id
            AND e.employment_status = 'Active'
        WHERE p.is_active = 1
          AND b.is_active = 1
        GROUP BY p.id, b.name, p.name, p.minimum_staff
        ORDER BY b.name, p.name
    """

    # Count only assignments belonging to active employees.
    query = query.replace(
        "COUNT(DISTINCT a.employee_id)",
        "COUNT(DISTINCT CASE WHEN e.employment_status = 'Active' "
        "THEN a.employee_id END)"
    )

    return _read_report(query, {"target_date": target_date})


def get_assignment_report(
    start_date: date | None = None,
    end_date: date | None = None,
    assignment_status: str = "All",
) -> pd.DataFrame:
    query = """
        SELECT
            a.id AS "Assignment ID",
            e.employee_code AS "Employee Code",
            e.full_name AS "Employee",
            e.employment_status AS "Employee Status",
            b.name AS "Brand",
            p.name AS "Process",
            a.start_date AS "Start Date",
            a.end_date AS "End Date",
            a.assignment_status AS "Assignment Status",
            a.is_primary AS "Primary Assignment"
        FROM assignments a
        JOIN employees e ON e.id = a.employee_id
        JOIN processes p ON p.id = a.process_id
        JOIN brands b ON b.id = p.brand_id
        WHERE 1 = 1
    """
    params = {}

    if start_date:
        query += " AND (a.end_date IS NULL OR a.end_date >= :start_date)"
        params["start_date"] = start_date

    if end_date:
        query += " AND a.start_date <= :end_date"
        params["end_date"] = end_date

    if assignment_status != "All":
        query += " AND a.assignment_status = :assignment_status"
        params["assignment_status"] = assignment_status

    query += " ORDER BY a.start_date DESC, e.full_name"
    return _read_report(query, params)


def get_leave_report(
    start_date: date | None = None,
    end_date: date | None = None,
    leave_status: str = "All",
) -> pd.DataFrame:
    query = """
        SELECT
            l.id AS "Leave Request ID",
            e.employee_code AS "Employee Code",
            e.full_name AS "Employee",
            COALESCE(p.name, 'Unassigned') AS "Pod",
            l.leave_type AS "Leave Type",
            l.start_date AS "Start Date",
            l.end_date AS "End Date",
            l.status AS "Status",
            l.reason AS "Reason",
            reviewer.full_name AS "Reviewed By",
            l.reviewed_at AS "Reviewed At"
        FROM leave_requests l
        JOIN employees e ON e.id = l.employee_id
        LEFT JOIN pods p ON p.id = e.pod_id
        LEFT JOIN employees reviewer ON reviewer.id = l.reviewed_by
        WHERE 1 = 1
    """
    params = {}

    if start_date:
        query += " AND l.end_date >= :start_date"
        params["start_date"] = start_date

    if end_date:
        query += " AND l.start_date <= :end_date"
        params["end_date"] = end_date

    if leave_status != "All":
        query += " AND l.status = :leave_status"
        params["leave_status"] = leave_status

    query += " ORDER BY l.start_date DESC, e.full_name"
    return _read_report(query, params)


def get_roster_report(
    year: int | None = None,
    month: int | None = None,
    roster_status: str = "All",
) -> pd.DataFrame:
    query = """
        SELECT
            rr.id AS "Roster ID",
            rr.month AS "Month",
            rr.year AS "Year",
            rr.status AS "Roster Status",
            rr.created_at AS "Created At",
            COUNT(DISTINCT re.id) AS "Roster Entries",
            (
                SELECT ra.status
                FROM roster_approvals ra
                WHERE ra.roster_id = rr.id
                ORDER BY ra.submitted_at DESC, ra.id DESC
                LIMIT 1
            ) AS "Latest Approval Status"
        FROM roster_runs rr
        LEFT JOIN roster_entries re ON re.roster_id = rr.id
        WHERE 1 = 1
    """
    params = {}

    if year is not None:
        query += " AND rr.year = :year"
        params["year"] = year

    if month is not None:
        query += " AND rr.month = :month"
        params["month"] = month

    if roster_status != "All":
        query += " AND rr.status = :roster_status"
        params["roster_status"] = roster_status

    query += """
        GROUP BY rr.id, rr.month, rr.year, rr.status, rr.created_at
        ORDER BY rr.year DESC, rr.month DESC, rr.id DESC
    """
    return _read_report(query, params)


def get_roster_entries_report(
    roster_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    query = """
        SELECT
            re.id AS "Entry ID",
            rr.id AS "Roster ID",
            rr.month AS "Roster Month",
            rr.year AS "Roster Year",
            re.roster_date AS "Roster Date",
            e.employee_code AS "Employee Code",
            e.full_name AS "Employee",
            b.name AS "Brand",
            p.name AS "Process",
            re.status AS "Entry Status"
        FROM roster_entries re
        JOIN roster_runs rr ON rr.id = re.roster_id
        JOIN employees e ON e.id = re.employee_id
        JOIN processes p ON p.id = re.process_id
        JOIN brands b ON b.id = p.brand_id
        WHERE 1 = 1
    """
    params = {}

    if roster_id is not None:
        query += " AND re.roster_id = :roster_id"
        params["roster_id"] = roster_id

    if start_date:
        query += " AND re.roster_date >= :start_date"
        params["start_date"] = start_date

    if end_date:
        query += " AND re.roster_date <= :end_date"
        params["end_date"] = end_date

    query += " ORDER BY re.roster_date, e.full_name"
    return _read_report(query, params)


def get_approval_report(
    start_date: date | None = None,
    end_date: date | None = None,
    approval_status: str = "All",
) -> pd.DataFrame:
    query = """
        SELECT
            ra.id AS "Approval ID",
            ra.roster_id AS "Roster ID",
            rr.month AS "Roster Month",
            rr.year AS "Roster Year",
            ra.status AS "Approval Status",
            submitter.full_name AS "Submitted By",
            reviewer.full_name AS "Reviewed By",
            ra.comments AS "Comments",
            ra.submitted_at AS "Submitted At",
            ra.reviewed_at AS "Reviewed At"
        FROM roster_approvals ra
        JOIN roster_runs rr ON rr.id = ra.roster_id
        LEFT JOIN employees submitter
            ON submitter.id = ra.submitted_by_employee_id
        LEFT JOIN employees reviewer
            ON reviewer.id = ra.reviewed_by_employee_id
        WHERE 1 = 1
    """
    params = {}

    if start_date:
        query += " AND DATE(ra.submitted_at) >= :start_date"
        params["start_date"] = start_date.isoformat()

    if end_date:
        query += " AND DATE(ra.submitted_at) <= :end_date"
        params["end_date"] = end_date.isoformat()

    if approval_status != "All":
        query += " AND ra.status = :approval_status"
        params["approval_status"] = approval_status

    query += " ORDER BY ra.submitted_at DESC"
    return _read_report(query, params)
