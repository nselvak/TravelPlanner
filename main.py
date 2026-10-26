
import sqlite3
from datetime import date, timedelta
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

            print(f"  {time} | {activity['name']}")
            print(f"    Location: {location}")
            print(f"    Estimated cost: {cost:.2f}")

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

    start_time = input("Start time (HH:MM, optional): ").strip()
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



def main():
    initialise_database()

    while True:
        print("\n=== Travel Planner ===")
        print("1. Create trip")
        print("2. List trips")
        print("3. View itinerary")
        print("4. Add activity")
        print("5. Exit")

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
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please choose 1–5.")

if __name__ == "__main__":
    main()
