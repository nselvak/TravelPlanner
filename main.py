
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
            SELECT day_date, notes
            FROM itinerary_days
            WHERE trip_id = ?
            ORDER BY day_date
            """,
            (trip_id,),
        ).fetchall()

    print(f"\nItinerary: {trip['name']}")
    for day in days:
        notes = day["notes"] or "No activities added yet."
        print(f"{day['day_date']} — {notes}")


def main():
    initialise_database()

    while True:
        print("\n=== Travel Planner ===")
        print("1. Create trip")
        print("2. List trips")
        print("3. View itinerary")
        print("4. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            create_trip()
        elif choice == "2":
            list_trips()
        elif choice == "3":
            view_itinerary()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please choose 1–4.")


if __name__ == "__main__":
    main()
