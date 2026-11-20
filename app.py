import duckdb
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Lithuanian Electricity Prices", page_icon="⚡", layout="wide")


@st.cache_data(ttl=3600)
def load_data():
    """Read all hourly data from the database and convert times to Vilnius time."""
    con = duckdb.connect("data/prices.duckdb", read_only=True)
    df = con.execute("SELECT * FROM hourly ORDER BY time_utc").df()
    con.close()
    df["time"] = (
        pd.to_datetime(df["time_utc"])
        .dt.tz_localize("UTC")
        .dt.tz_convert("Europe/Vilnius")
        .dt.tz_localize(None)
    )
    return df


df = load_data()

# ---------- Header ----------
st.title("⚡ Lithuanian Electricity Prices")
st.caption(
    "Nord Pool day-ahead prices for Lithuania alongside Vilnius weather. "
    "Data is collected automatically every day by a Python + DuckDB pipeline running on GitHub Actions."
)

# ---------- Date filter ----------
total_days = max((df["time"].max() - df["time"].min()).days + 1, 2)
days = st.slider("Show the last N days", min_value=1, max_value=total_days, value=min(7, total_days))
view = df[df["time"] >= df["time"].max() - pd.Timedelta(days=days)]

# ---------- Key numbers ----------
latest = view.iloc[-1]
cheapest = view.loc[view["price_eur_mwh"].idxmin()]
priciest = view.loc[view["price_eur_mwh"].idxmax()]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest price", f"€{latest['price_eur_mwh']:.0f}/MWh")
c1.caption(latest["time"].strftime("%a %d %b, %H:00"))
c2.metric("Average price", f"€{view['price_eur_mwh'].mean():.0f}/MWh")
c2.caption(f"Last {days} days")
c3.metric("Cheapest hour", f"€{cheapest['price_eur_mwh']:.0f}/MWh")
c3.caption(cheapest["time"].strftime("%a %d %b, %H:00"))
c4.metric("Most expensive hour", f"€{priciest['price_eur_mwh']:.0f}/MWh")
c4.caption(priciest["time"].strftime("%a %d %b, %H:00"))

# ---------- Price over time ----------
st.subheader("Price over time (€/MWh)")
st.line_chart(view.set_index("time")["price_eur_mwh"])

# ---------- Typical day ----------
left, right = st.columns(2)

with left:
    st.subheader("Average price by hour of day")
    by_hour = view.groupby(view["time"].dt.hour)["price_eur_mwh"].mean()
    by_hour.index.name = "hour"
    st.bar_chart(by_hour)
    best_hour = int(by_hour.idxmin())
    worst_hour = int(by_hour.idxmax())
    st.caption(
        f"Cheapest time of day on average: {best_hour:02d}:00. "
        f"Most expensive: {worst_hour:02d}:00."
    )

with right:
    st.subheader("Does wind make power cheaper?")
    st.scatter_chart(
        view[["wind_kmh", "price_eur_mwh"]],
        x="wind_kmh",
        y="price_eur_mwh",
        x_label="Wind speed (km/h)",
        y_label="Price (€/MWh)",
    )
    corr = view["wind_kmh"].corr(view["price_eur_mwh"])
    st.caption(f"Correlation between wind speed and price: {corr:.2f} (negative means more wind, lower prices).")

# ---------- Weather ----------
st.subheader("Vilnius weather")
st.line_chart(view.set_index("time")[["temp_c", "wind_kmh"]])

# ---------- Raw data ----------
with st.expander("See the raw data"):
    table = view[["time", "price_eur_mwh", "temp_c", "wind_kmh"]].sort_values("time", ascending=False)
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button("Download as CSV", table.to_csv(index=False), "lt_electricity_prices.csv", "text/csv")