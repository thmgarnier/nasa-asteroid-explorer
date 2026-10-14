
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="NASA Asteroid Explorer",
    page_icon="☄️",
    layout="wide",
)

st.title("☄️ NASA Asteroid Explorer")
st.caption(
    "Explore near-Earth asteroid approaches using NASA's public API."
)

@st.cache_data(ttl=3600)
def load_asteroids(start_date, end_date):
    response = requests.get(
        "https://api.nasa.gov/neo/rest/v1/feed",
        params={
            "start_date": start_date,
            "end_date": end_date,
            "api_key": "DEMO_KEY",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    rows = []
    for asteroids in payload["near_earth_objects"].values():
        for asteroid in asteroids:
            for approach in asteroid["close_approach_data"]:
                rows.append({
                    "Asteroid": asteroid["name"],
                    "Approach date": approach["close_approach_date"],
                    "Distance (km)": float(
                        approach["miss_distance"]["kilometers"]
                    ),
                    "Velocity (km/h)": float(
                        approach["relative_velocity"][
                            "kilometers_per_hour"
                        ]
                    ),
                    "Max diameter (km)": float(
                        asteroid["estimated_diameter"]["kilometers"][
                            "estimated_diameter_max"
                        ]
                    ),
                    "Potentially hazardous": asteroid[
                        "is_potentially_hazardous_asteroid"
                    ],
                })

    return pd.DataFrame(rows)


today = date.today()
start = st.date_input("Start date", today)
end = st.date_input(
    "End date",
    min(today + timedelta(days=1), today + timedelta(days=6)),
)

if start > end:
    st.error("The start date must be on or before the end date.")
    st.stop()

if (end - start).days > 6:
    st.error("Choose a date range of no more than seven calendar days.")
    st.stop()

try:
    df = load_asteroids(start.isoformat(), end.isoformat())

    if df.empty:
        st.info("No asteroid approaches were returned for these dates.")
        st.stop()

    hazardous_only = st.checkbox(
        "Show potentially hazardous asteroids only"
    )
    view = df.copy()

    if hazardous_only:
        view = view[view["Potentially hazardous"]]

    c1, c2, c3 = st.columns(3)
    c1.metric("Asteroid approaches", len(view))

    if not view.empty:
        c2.metric(
            "Closest approach (km)",
            f"{view['Distance (km)'].min():,.0f}",
        )
        c3.metric(
            "Maximum velocity (km/h)",
            f"{view['Velocity (km/h)'].max():,.0f}",
        )
    else:
        c2.metric("Closest approach (km)", "—")
        c3.metric("Maximum velocity (km/h)", "—")

    st.subheader("Approach data")
    st.dataframe(
        view.sort_values("Distance (km)"),
        use_container_width=True,
        hide_index=True,
    )

    if not view.empty:
        st.subheader("Approach distance")
        chart = view.set_index("Asteroid")[["Distance (km)"]]
        st.bar_chart(chart.head(15))

    st.caption(
        "Source: NASA Near Earth Object Web Service. "
        "A potentially hazardous classification does not mean "
        "an asteroid is predicted to impact Earth."
    )

except requests.RequestException as exc:
    st.error(f"Could not retrieve NASA data: {exc}")
except (ValueError, KeyError) as exc:
    st.error(f"Could not process the NASA response: {exc}")
