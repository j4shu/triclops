import os
import requests
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth


BASE_URL = "https://intervals.icu/api/v1"


def _auth():
    return HTTPBasicAuth("API_KEY", os.environ["INTERVALS_API_KEY"])


def _athlete_id():
    return os.environ["INTERVALS_ATHLETE_ID"]


def _date_range(window):
    """Return (oldest, newest) date strings for the given window label."""
    today = datetime.now().date()
    windows = {
        "7d": 7,
        "1mo": 30,
        "42d": 42,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
    }
    days = windows.get(window, 42)
    oldest = today - timedelta(days=days)
    return oldest.isoformat(), today.isoformat()


def get_activities(window="42d"):
    """Fetch activities within the time window."""
    oldest, newest = _date_range(window)
    url = f"{BASE_URL}/athlete/{_athlete_id()}/activities"
    resp = requests.get(
        url,
        params={"oldest": oldest, "newest": newest},
        auth=_auth(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_wellness(window="42d"):
    """Fetch wellness data within the time window."""
    oldest, newest = _date_range(window)
    url = f"{BASE_URL}/athlete/{_athlete_id()}/wellness"
    resp = requests.get(
        url,
        params={"oldest": oldest, "newest": newest},
        auth=_auth(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_athlete_settings():
    """Fetch athlete profile and zone settings."""
    url = f"{BASE_URL}/athlete/{_athlete_id()}"
    resp = requests.get(url, auth=_auth(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_events():
    """Fetch planned events / races."""
    oldest = (datetime.now().date() - timedelta(days=365)).isoformat()
    newest = (datetime.now().date() + timedelta(days=365)).isoformat()
    url = f"{BASE_URL}/athlete/{_athlete_id()}/events"
    resp = requests.get(
        url,
        params={"oldest": oldest, "newest": newest},
        auth=_auth(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def build_training_summary(window="42d"):
    """Pull all relevant data and build a structured summary for Claude."""
    activities = get_activities(window)
    wellness = get_wellness(window)

    try:
        settings = get_athlete_settings()
    except Exception:
        settings = {}

    try:
        events = get_events()
    except Exception:
        events = []

    # Summarize activities
    activity_summaries = []
    for a in activities:
        summary = {
            "date": a.get("start_date_local", "")[:10],
            "type": a.get("type", ""),
            "name": a.get("name", ""),
            "duration_secs": a.get("moving_time", a.get("elapsed_time", 0)),
            "distance_m": a.get("distance", 0),
            "icu_training_load": a.get("icu_training_load", 0),
            "icu_intensity": a.get("icu_intensity", 0),
            "average_heartrate": a.get("average_heartrate", 0),
            "average_speed": a.get("average_speed", 0),
            "average_watts": a.get("average_watts", 0),
            "normalized_power": a.get("icu_weighted_avg_watts", 0),
            "total_elevation_gain": a.get("total_elevation_gain", 0),
            "pace_or_speed": a.get("average_speed", 0),
        }
        activity_summaries.append(summary)

    # Summarize wellness
    wellness_summaries = []
    for w in wellness:
        ws = {
            "date": w.get("id", ""),
            "ctl": w.get("ctl", 0),
            "atl": w.get("atl", 0),
            "rampRate": w.get("rampRate", 0),
            "restingHR": w.get("restingHR", 0),
            "hrv": w.get("hrv", 0),
            "sleep_quality": w.get("sleepQuality", 0),
            "fatigue": w.get("fatigue", 0),
            "mood": w.get("mood", 0),
            "soreness": w.get("soreness", 0),
            "weight": w.get("weight", 0),
        }
        wellness_summaries.append(ws)

    # Key settings
    athlete_info = {}
    if settings:
        athlete_info = {
            "ftp": settings.get("ftp", 0),
            "lthr": settings.get("lthr", {}),
            "max_hr": settings.get("max_hr", 0),
            "weight": settings.get("weight", 0),
            "sport_settings": settings.get("sportSettings", []),
        }

    return {
        "window": window,
        "athlete": athlete_info,
        "events": (
            [
                {
                    "name": e.get("name", ""),
                    "date": e.get("start_date_local", "")[:10],
                    "category": e.get("category", ""),
                    "type": e.get("type", ""),
                }
                for e in events
            ]
            if events
            else []
        ),
        "activities": activity_summaries,
        "wellness": wellness_summaries,
    }
