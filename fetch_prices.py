import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

# Get the last 7 days of prices
end = datetime.now(timezone.utc)
start = end - timedelta(days=7)

url = "https://dashboard.elering.ee/api/nps/price"
params = {
    "start": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    "end": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
}

response = requests.get(url, params=params, timeout=30)
response.raise_for_status()
data = response.json()

# Take only Lithuania's prices
df = pd.DataFrame(data["data"]["lt"])
df["time"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert("Europe/Vilnius")
df = df[["time", "price"]]

print(df.head(10))
print("\nRows:", len(df))
print("Average price (€/MWh):", round(df["price"].mean(), 2))
print("Max:", df["price"].max(), " Min:", df["price"].min())