
import sqlite3
from datetime import date, timedelta, datetime
from pathlib import Path

DB_PATH = Path(__file__).with_name("travel.db")


def connect_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialise_database():
    with connect_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (end_date >= start_date)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS itinerary_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER NOT NULL,
                day_date TEXT NOT NULL,
                notes TEXT DEFAULT '',
                FOREIGN KEY (trip_id)
                    REFERENCES trips(id)
                    ON DELETE CASCADE,
                UNIQUE (trip_id, day_date)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                itinerary_day_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                start_time TEXT,
                location TEXT DEFAULT '',
                estimated_cost REAL NOT NULL DEFAULT 0
                    CHECK (estimated_cost >= 0),
                notes TEXT DEFAULT '',
                FOREIGN KEY (itinerary_day_id)
                    REFERENCES itinerary_days(id)
                    ON DELETE CASCADE
            )
        """)        


####################################
# Validation 
####################################

def normalize_time(value):
    """Accept common time formats and return HH:MM.

    Examples:
        2350 -> 23:50
        930  -> 09:30
        9    -> 09:00

    Returns an empty string for blank input and None for invalid input.
    """
    value = value.strip()

    if not value:
        return ""

    try:
        if ":" in value:
            # Accept formats such as 9:30 and 09:30.
            parts = value.split(":")

            if (
                len(parts) != 2
                or not parts[0].isdigit()
                or len(parts[0]) not in (1, 2)
                or not parts[1].isdigit()
                or len(parts[1]) != 2
            ):
                return None

            hour = int(parts[0])
            minute = int(parts[1])

        elif value.isdigit():
            # Compact formats: 9, 09, 930, 0930, 2350.
            if len(value) <= 2:
                hour = int(value)
                minute = 0
            elif len(value) == 3:
                hour = int(value[0])
                minute = int(value[1:])
            elif len(value) == 4:
                hour = int(value[:2])
                minute = int(value[2:])
            else:
                return None
        else:
            return None

        normalised = f"{hour:02d}:{minute:02d}"

        # Reject impossible times such as 25:90 or 24:00.
        return datetime.strptime(normalised, "%H:%M").strftime("%H:%M")

    except ValueError:
        return None



####################################
# Actual Functions
####################################
def create_trip():
    name = input("Trip name: ").strip()

    if not name:
        print("Trip name cannot be empty.")
        return

    try:
        start_date = date.fromisoformat(
            input("Start date (YYYY-MM-DD): ").strip()
        )
        end_date = date.fromisoformat(
            input("End date (YYYY-MM-DD): ").strip()
        )
    except ValueError:
        print("Invalid date. Please use YYYY-MM-DD.")
        return

    if end_date < start_date:
        print("End date cannot be before the start date.")
        return

    with connect_db() as connection:
        cursor = connection.execute(
            """
            INSERT INTO trips (name, start_date, end_date)
            VALUES (?, ?, ?)
            """,
            (name, start_date.isoformat(), end_date.isoformat()),
        )

        trip_id = cursor.lastrowid
        current_date = start_date

        while current_date <= end_date:
            connection.execute(
                """
                INSERT INTO itinerary_days (trip_id, day_date)
                VALUES (?, ?)
                """,
                (trip_id, current_date.isoformat()),
            )
            current_date += timedelta(days=1)

    print(f"Trip '{name}' created successfully.")


def list_trips():
    with connect_db() as connection:
        trips = connection.execute(
            "SELECT * FROM trips ORDER BY start_date"
        ).fetchall()

    if not trips:
        print("No trips saved yet.")
        return

    print("\nYour trips:")
    for trip in trips:
        print(
            f"ID: {trip['id']} | {trip['name']} | "
            f"{trip['start_date']} to {trip['end_date']}"
        )



def view_itinerary():
    try:
        trip_id = int(input("Enter trip ID: ").strip())
    except ValueError:
        print("Please enter a valid numeric trip ID.")
        return

    with connect_db() as connection:
        trip = connection.execute(
            "SELECT * FROM trips WHERE id = ?",
            (trip_id,),
        ).fetchone()

        if trip is None:
            print("Trip not found.")
            return

        days = connection.execute(
            """
            SELECT id, day_date, notes
            FROM itinerary_days
            WHERE trip_id = ?
            ORDER BY day_date
            """,
            (trip_id,),
        ).fetchall()

        activities = connection.execute(
            """
            SELECT
                a.id,
                a.itinerary_day_id,
                a.name,
                a.start_time,
                a.location,
                a.estimated_cost,
                a.notes
            FROM activities AS a
            JOIN itinerary_days AS d
                ON d.id = a.itinerary_day_id
            WHERE d.trip_id = ?
            ORDER BY d.day_date, a.start_time, a.id
            """,
            (trip_id,),
        ).fetchall()

    print(f"\n=== Itinerary: {trip['name']} ===")
    print(f"{trip['start_date']} to {trip['end_date']}")

    total_cost = 0.0

    for day in days:
        print(f"\n--- {day['day_date']} ---")
        daily_total = 0.0

        if day["notes"]:
            print(f"Notes: {day['notes']}")

        day_activities = [
            activity
            for activity in activities
            if activity["itinerary_day_id"] == day["id"]
        ]

        if not day_activities:
            print("  No activities planned.")
            continue

        for activity in day_activities:
            time = activity["start_time"] or "Time TBD"
            location = activity["location"] or "Location TBD"
            cost = activity["estimated_cost"]
            total_cost += cost
            daily_total += cost

            print(f"  ID {activity['id']} | {time} | {activity['name']}")
            print(f"    Location: {location}")
            print(f"    Estimated cost: {cost:.2f}")
            print(f"  Daily activity total: {daily_total:.2f}")

            if activity["notes"]:
                print(f"    Notes: {activity['notes']}")

    print(f"\nEstimated total activity cost: {total_cost:.2f}")


def add_activity():
    try:
        trip_id = int(input("Trip ID: ").strip())
    except ValueError:
        print("Please enter a valid trip ID.")
        return

    with connect_db() as connection:
        trip = connection.execute(
            "SELECT id, name FROM trips WHERE id = ?",
            (trip_id,),
        ).fetchone()

        if trip is None:
            print("Trip not found.")
            return

        days = connection.execute(
            """
            SELECT id, day_date
            FROM itinerary_days
            WHERE trip_id = ?
            ORDER BY day_date
            """,
            (trip_id,),
        ).fetchall()

    print(f"\nTrip: {trip['name']}")
    for day in days:
        print(f"Day ID: {day['id']} | {day['day_date']}")

    try:
        day_id = int(input("Choose itinerary day ID: ").strip())
    except ValueError:
        print("Please enter a valid day ID.")
        return

    if not any(day["id"] == day_id for day in days):
        print("That day does not belong to this trip.")
        return

    name = input("Activity name: ").strip()
    if not name:
        print("Activity name cannot be empty.")
        return

    start_time_input = input(
        "Start time (e.g. 930, 2350, or 09:30): "
    )
    # noramlizing time
    start_time = normalize_time(start_time_input)

    if start_time is None:
        print("Invalid time. Try 930, 2350, or 09:30.")
        return

    if start_time:
        print(f"Interpreted time: {start_time}")
    
    location = input("Location (optional): ").strip()
    cost_text = input("Estimated cost (default 0): ").strip()
    notes = input("Notes (optional): ").strip()

    try:
        estimated_cost = float(cost_text) if cost_text else 0.0
        if estimated_cost < 0:
            raise ValueError
    except ValueError:
        print("Cost must be a non-negative number.")
        return

    with connect_db() as connection:
        connection.execute(
            """
            INSERT INTO activities (
                itinerary_day_id, name, start_time,
                location, estimated_cost, notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                day_id,
                name,
                start_time or None,
                location,
                estimated_cost,
                notes,
            ),
        )

    print("Activity added successfully.")

    
def edit_activity():
    try:
        activity_id = int(input("Activity ID to edit: ").strip())
    except ValueError:
        print("Please enter a valid activity ID.")
        return

    with connect_db() as connection:
        activity = connection.execute(
            """
            SELECT id, name, start_time, location, estimated_cost, notes
            FROM activities
            WHERE id = ?
            """,
            (activity_id,),
        ).fetchone()

    if activity is None:
        print("Activity not found.")
        return

    print(f"\nEditing: {activity['name']}")
    print("Press Enter to keep the current value.")

    name = input(f"Name [{activity['name']}]: ").strip()
    start_time_input = input(
        f"Start time [{activity['start_time'] or ''}]: "
        " "
    ).strip()

    if start_time_input:
        start_time = normalize_time(start_time_input)

        if start_time is None:
            print("Invalid time. Try 930, 2350, or 09:30.")
            return
    else:
        # Enter keeps the existing time.
        start_time = activity["start_time"]

    location = input(
        f"Location [{activity['location'] or ''}]: "
    ).strip()
    cost_text = input(
        f"Estimated cost [{activity['estimated_cost']:.2f}]: "
    ).strip()
    notes = input(f"Notes [{activity['notes'] or ''}]: ").strip()

    try:
        estimated_cost = (
            float(cost_text)
            if cost_text
            else activity["estimated_cost"]
        )
        if estimated_cost < 0:
            raise ValueError
    except ValueError:
        print("Cost must be a non-negative number. No changes saved.")
        return

    updated_name = name or activity["name"]
    updated_time = (
        start_time if start_time else activity["start_time"]
    )
    updated_location = location or activity["location"]
    updated_notes = notes or activity["notes"]

    with connect_db() as connection:
        connection.execute(
            """
            UPDATE activities
            SET name = ?,
                start_time = ?,
                location = ?,
                estimated_cost = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                updated_name,
                updated_time,
                updated_location,
                estimated_cost,
                updated_notes,
                activity_id,
            ),
        )

    print("Activity updated successfully.")


def delete_activity():
    try:
        activity_id = int(input("Activity ID to delete: ").strip())
    except ValueError:
        print("Please enter a valid activity ID.")
        return

    with connect_db() as connection:
        activity = connection.execute(
            "SELECT id, name FROM activities WHERE id = ?",
            (activity_id,),
        ).fetchone()

        if activity is None:
            print("Activity not found.")
            return

        print(f"Activity: {activity['name']}")
        confirmation = input("Delete this activity? (y/N): ").strip().lower()

        if confirmation != "y":
            print("Deletion cancelled.")
            return

        connection.execute(
            "DELETE FROM activities WHERE id = ?",
            (activity_id,),
        )

    print("Activity deleted successfully.")




def main():
    initialise_database()

    while True:
        print("\n=== Travel Planner ===")
        print("1. Create trip")
        print("2. List trips")
        print("3. View itinerary")
        print("4. Add activity")
        print("5. Edit activity")
        print("6. Delete activity")
        print("7. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            create_trip()
        elif choice == "2":
            list_trips()
        elif choice == "3":
            view_itinerary()
        elif choice == "4":
            add_activity()
        elif choice == "5":
            edit_activity()
        elif choice == "6":
            delete_activity()
        elif choice == "7":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please choose 1–7.")

if __name__ == "__main__":
    main()
