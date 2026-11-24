from datetime import date

from src.database.models import OperatingCalendar, PublicHoliday


# Convert Python weekday numbers into calendar day names.
# Monday = 0 and Sunday = 6.
WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def get_calendar_by_process_id(db, process_id):
    """Get the operating calendar assigned to a process."""
    return (
        db.query(OperatingCalendar)
        .filter(OperatingCalendar.process_id == process_id)
        .first()
    )


def get_calendar_holidays(db, calendar_id):
    """Get all public holidays configured for a calendar."""
    return (
        db.query(PublicHoliday)
        .filter(PublicHoliday.calendar_id == calendar_id)
        .order_by(PublicHoliday.holiday_date)
        .all()
    )


def get_holiday_for_date(db, calendar_id, target_date):
    """Check whether a particular date is a public holiday."""
    return (
        db.query(PublicHoliday)
        .filter(
            PublicHoliday.calendar_id == calendar_id,
            PublicHoliday.holiday_date == target_date,
        )
        .first()
    )


def is_public_holiday(db, calendar_id, target_date):
    """Return True if the date is a public holiday."""
    holiday = get_holiday_for_date(db, calendar_id, target_date)
    return holiday is not None


def is_working_day(db, process_id, target_date):
    """
    Check whether a process operates on a particular date.

    A date is a working day when:
    1. The process has an active operating calendar.
    2. The weekday is included in that calendar.
    3. The date is not a public holiday in that calendar.
    """
    calendar = get_calendar_by_process_id(db, process_id)

    if calendar is None:
        raise ValueError(
            f"No operating calendar found for process ID {process_id}."
        )

    if not calendar.is_active:
        return False

    weekday_name = WEEKDAY_NAMES[target_date.weekday()]

    working_days = [
        day.strip()
        for day in calendar.working_days.split(",")
        if day.strip()
    ]

    if weekday_name not in working_days:
        return False

    if is_public_holiday(db, calendar.id, target_date):
        return False

    return True


def get_working_days_for_process(db, process_id):
    """Return the configured working days for a process."""
    calendar = get_calendar_by_process_id(db, process_id)

    if calendar is None:
        raise ValueError(
            f"No operating calendar found for process ID {process_id}."
        )

    return [
        day.strip()
        for day in calendar.working_days.split(",")
        if day.strip()
    ]