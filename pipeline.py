import os
import time
from datetime import datetime, timedelta, timezone

import duckdb
import pandas as pd
import requests

DB_PATH = "data/prices.duckdb"
DAYS = 7


def get_json(url, params):
    """Call an API, retrying up to 5 times if it fails."""
    for attempt in range(1, 6):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            print(f"Attempt {attempt} failed: {error}")
            if attempt == 5:
                raise
            time.sleep(attempt * 10)


def fetch_prices():
    """EXTRACT: Lithuanian electricity prices (15-minute) -> hourly averages."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS)
    data = get_json(
        "https://dashboard.elering.ee/api/nps/price",
        {
            "start": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "end": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        },
    )
    df = pd.DataFrame(data["data"]["lt"])
    df["time"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    hourly = df.set_index("time")["price"].resample("1h").mean().reset_index()
    return hourly


def fetch_weather():
    """EXTRACT: hourly temperature and wind for Vilnius."""
    data = get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": 54.69,
            "longitude": 25.28,
            "hourly": "temperature_2m,wind_speed_10m",
            "past_days": DAYS,
            "forecast_days": 1,
            "timezone": "GMT",
        },
    )
    weather = pd.DataFrame(data["hourly"])
    weather["time"] = pd.to_datetime(weather["time"], utc=True)
    return weather.rename(columns={"temperature_2m": "temp_c", "wind_speed_10m": "wind_kmh"})


def main():
    print("Fetching prices...")
    prices = fetch_prices()
    print("Fetching weather...")
    weather = fetch_weather()

    # TRANSFORM: match prices and weather by hour, store times as UTC
    combined = prices.merge(weather, on="time", how="inner").dropna()
    combined["time"] = combined["time"].dt.tz_localize(None)
    combined = combined.rename(columns={"time": "time_utc", "price": "price_eur_mwh"})

    # LOAD: save into DuckDB, replacing hours we already have (no duplicates)
    os.makedirs("data", exist_ok=True)
    con = duckdb.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS hourly (
            time_utc      TIMESTAMP PRIMARY KEY,
            price_eur_mwh DOUBLE,
            temp_c        DOUBLE,
            wind_kmh      DOUBLE
        )
    """)
    con.register("new_rows", combined)
    con.execute("""
        INSERT OR REPLACE INTO hourly
        SELECT time_utc, price_eur_mwh, temp_c, wind_kmh FROM new_rows
    """)

    count, first, last = con.execute(
        "SELECT COUNT(*), MIN(time_utc), MAX(time_utc) FROM hourly"
    ).fetchone()
    print(f"\nSaved {len(combined)} hours this run.")
    print(f"Database now holds {count} hours, from {first} to {last} (UTC).")
    print("\nLatest 5 rows:")
    print(con.execute("SELECT * FROM hourly ORDER BY time_utc DESC LIMIT 5").df())
    con.close()


if __name__ == "__main__":
    main()