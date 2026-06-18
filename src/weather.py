"""Task 1 - Weather.

Pull today plus a 6-day Toronto forecast from Open-Meteo (no API key) and
return the weather block matching the renderer schema.
"""

from __future__ import annotations

import datetime as dt

import requests

from . import config

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

_DAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _day_label(iso_date: str) -> str:
    """ISO date string (YYYY-MM-DD) -> short weekday label."""
    d = dt.date.fromisoformat(iso_date)
    return _DAY_ABBR[d.weekday()]


def get_weather() -> dict:
    """Return the weather block: condition, high, low, rain, wind, icon, week[6]."""
    params = {
        "latitude": config.TORONTO_LAT,
        "longitude": config.TORONTO_LON,
        "timezone": config.TIMEZONE,
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "daily": (
            "temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,weather_code,wind_speed_10m_max"
        ),
        "wind_speed_unit": "kmh",
        "forecast_days": 7,
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    daily = data["daily"]
    today_code = int(daily["weather_code"][0])

    week = []
    for i, iso_date in enumerate(daily["time"][:6]):
        week.append(
            {
                "day": _day_label(iso_date),
                "icon": config.weather_icon(int(daily["weather_code"][i])),
                "hi": round(daily["temperature_2m_max"][i]),
                "lo": round(daily["temperature_2m_min"][i]),
            }
        )

    rain_pct = daily["precipitation_probability_max"][0]
    wind_kmh = round(daily["wind_speed_10m_max"][0])

    return {
        "condition": config.weather_condition(today_code),
        "high": round(daily["temperature_2m_max"][0]),
        "low": round(daily["temperature_2m_min"][0]),
        "rain": f"{int(rain_pct)}%" if rain_pct is not None else "0%",
        "wind": f"{wind_kmh} km/h gusts",
        "icon": config.weather_icon(today_code),
        "week": week,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(get_weather(), indent=2, ensure_ascii=False))
