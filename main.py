from datetime import date, timedelta

trip_name = input("Trip name: ")
start_date = date.fromisoformat(input("Start date (YYYY-MM-DD): "))
end_date = date.fromisoformat(input("End date (YYYY-MM-DD): "))

if end_date < start_date:
    print("Error: end date cannot be before start date.")
else:
    print(f"\nTrip: {trip_name}")
    print(f"Duration: {(end_date - start_date).days + 1} days")
    print("\nItinerary:")

    current_date = start_date
    while current_date <= end_date:
        print(f"{current_date} - No activities planned")
        current_date += timedelta(days=1)
