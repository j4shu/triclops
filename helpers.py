from datetime import datetime, timedelta
from os import environ

from requests import get
from requests.auth import HTTPBasicAuth

BASE_URL = "https://intervals.icu/api/v1"


def api_get_athlete(path, params=None):
    auth = HTTPBasicAuth("API_KEY", environ["INTERVALS_API_KEY"])
    athlete_id = environ["INTERVALS_ATHLETE_ID"]
    url = f"{BASE_URL}/athlete/{athlete_id}/{path}"
    resp = get(url, params=params, auth=auth, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_get_activity_intervals(activity_id):
    auth = HTTPBasicAuth("API_KEY", environ["INTERVALS_API_KEY"])
    url = f"{BASE_URL}/activity/{activity_id}/intervals"
    resp = get(url, auth=auth, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_date_range(past, future=None):
    today = datetime.now().date()
    windows = {
        "1d": 1,
        "4d": 4,
        "7d": 7,
        "1mo": 30,
        "42d": 42,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
    }
    days = windows.get(past, 42)
    oldest = today - timedelta(days=days)
    if future:
        future_days = windows.get(future, 42)
        newest = today + timedelta(days=future_days)
    else:
        newest = today
    return oldest.isoformat(), newest.isoformat()


def strip_empty(o):
    if isinstance(o, dict):
        return {
            k: strip_empty(v)
            for k, v in o.items()
            # filter out null, boolean, and zero values
            if v is not None and not isinstance(v, bool) and not v == 0.0
        }
    if isinstance(o, list):
        return [strip_empty(i) for i in o]
    return o


def seconds_to_hhmmss(s):
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    return f"{h}h{m:02d}m{sec:02d}s"


def meters_to_miles(m):
    return f"{round(m * 0.000621371, 2)}mi"


def meters_to_yards(m):
    yards = m * 1.09361
    rounded = round(yards / 25) * 25
    return f"{rounded}yd"


def mps_to_mph(mps):
    return f"{round(mps * 2.23694, 2)}mph"


def mps_to_min_per_mile(mps):
    total_secs = 1609.34 / mps
    m, s = divmod(int(total_secs), 60)
    return f"{m}:{s:02d}/mi"


def mps_to_min_per_100yds(mps):
    total_secs = (100 * 0.9144) / mps
    m, s = divmod(int(total_secs), 60)
    return f"{m}:{s:02d}/100yd"


# "interval_summary": [
#     "2x 388m 138bpm",
#     "2x 45m 131bpm",
#     "6x 68m 140bpm",
#     "1x 274m 144bpm",
#     "1x 182m 143bpm",
#     "1x 91m 142bpm",
#     "1x 91m 143bpm"
# ],
def parse_swim_interval_summary(summary):
    intervals = []
    for s in summary:
        parts = s.split()
        new_parts = []
        for p in parts:
            if p.endswith("m") and not p.endswith("bpm"):
                new_parts.append(meters_to_yards(float(p[:-1])))
            else:
                new_parts.append(p)
        intervals.append(" ".join(new_parts))
    return intervals
