
from datetime import date, time

from src.database.connection import SessionLocal
from src.database.models import Process, OperatingCalendar, PublicHoliday


# Working-day rules for each process calendar
WORKING_DAY_RULES = {
    "year_round": (
        "Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday"
    ),
    "daily": (
        "Monday,Tuesday,Wednesday,Thursday,Friday,Saturday"
    ),
    "weekdays": (
        "Monday,Tuesday,Wednesday,Thursday,Friday"
    ),
}

# Sample holidays for the demonstration database
SAMPLE_HOLIDAYS = [
    (date(2026, 12, 25), "Christmas Day"),
    (date(2027, 1, 26), "Republic Day"),
    (date(2027, 8, 15), "Independence Day"),
    (date(2027, 10, 2), "Gandhi Jayanti"),
]


def seed_calendar_data():
    db = SessionLocal()

    try:
        processes = db.query(Process).all()

        if not processes:
            print("No processes found. Seed the main data first.")
            return

        calendars_created = 0
        holidays_created = 0

        for process in processes:

            # Read the existing calendar type from the Process table
            calendar_type = process.operating_calendar or "daily"

            working_days = WORKING_DAY_RULES.get(
                calendar_type,
                WORKING_DAY_RULES["daily"]
            )

            # Find an existing calendar for this process
            calendar = (
                db.query(OperatingCalendar)
                .filter_by(process_id=process.id)
                .first()
            )

            # Create a calendar only if one doesn't already exist
            if calendar is None:
                calendar = OperatingCalendar(
                    process_id=process.id,
                    calendar_name=f"{process.name} Calendar",
                    working_days=working_days,
                    opening_time=time(9, 0),
                    closing_time=time(18, 0),
                    is_active=True,
                )

                db.add(calendar)
                db.flush()
                calendars_created += 1

            # Year-round processes work even on public holidays
            if calendar_type == "year_round":
                continue

            # Add sample holidays without creating duplicates
            for holiday_date, holiday_name in SAMPLE_HOLIDAYS:

                existing_holiday = (
                    db.query(PublicHoliday)
                    .filter_by(
                        calendar_id=calendar.id,
                        holiday_date=holiday_date
                    )
                    .first()
                )

                if existing_holiday is None:
                    holiday = PublicHoliday(
                        calendar_id=calendar.id,
                        holiday_date=holiday_date,
                        holiday_name=holiday_name,
                        description="Sample public holiday for RosterIQ",
                    )

                    db.add(holiday)
                    holidays_created += 1

        db.commit()

        print("Calendar data seeded successfully!")
        print(f"New calendars created: {calendars_created}")
        print(f"New holidays created: {holidays_created}")

    except Exception as error:
        db.rollback()
        print(f"Error while seeding calendar data: {error}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_calendar_data()
