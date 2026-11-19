import requests
import pandas as pd

# Vilnius coordinates, last 7 days of hourly weather
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": 54.69,
    "longitude": 25.28,
    "hourly": "temperature_2m,wind_speed_10m",
    "past_days": 7,
    "forecast_days": 1,
    "timezone": "GMT",
}

response = requests.get(url, params=params, timeout=30)
response.raise_for_status()
data = response.json()

weather = pd.DataFrame(data["hourly"])
weather["time"] = pd.to_datetime(weather["time"], utc=True).dt.tz_convert("Europe/Vilnius")
weather = weather.rename(columns={
    "temperature_2m": "temp_c",
    "wind_speed_10m": "wind_kmh",
})

print(weather.head(10))
print("\nRows:", len(weather))
print("Average temp (°C):", round(weather["temp_c"].mean(), 1))
print("Average wind (km/h):", round(weather["wind_kmh"].mean(), 1))