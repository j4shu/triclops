from json import load
from pathlib import Path

from helpers import *

ATHLETE_FILE = Path(".athlete")


def get_activities(past, raw=False):
    oldest, newest = get_date_range(past)
    response = api_get("activities", params={"oldest": oldest, "newest": newest})
    if raw:
        return response
    data = [
        {
            # Identity
            "date": a.get("start_date_local", "")[:10],
            "type": a.get("type"),
            "name": a.get("name"),
            # Duration & distance
            "duration": seconds_to_hhmmss(a.get("moving_time", a.get("elapsed_time"))),
            "distance": calculate_distance(a.get("distance"), a.get("type")),
            # Training load & fitness
            "training_load": a.get("icu_training_load"),
            "intensity": a.get("icu_intensity"),
            "atl": a.get("icu_atl"),
            "ctl": a.get("icu_ctl"),
            "trimp": a.get("trimp"),
            "joules": a.get("joules"),
            # Heart rate
            "average_heartrate": a.get("average_heartrate"),
            "max_heartrate": a.get("max_heartrate"),
            "hr_zones": a.get("icu_hr_zones"),
            "lthr": a.get("lthr"),
            # Cycling-specific
            "average_watts": a.get("icu_average_watts"),
            "normalized_power": a.get("icu_weighted_avg_watts"),
            "athlete_ftp": a.get("icu_ftp"),
            "time_in_zones": a.get("icu_zone_times"),
            "decoupling": a.get("decoupling"),
            "efficiency_factor": a.get("icu_efficiency_factor"),
            "variability_index": a.get("icu_variability_index"),
            "polarization_index": a.get("polarization_index"),
            "strain_score": a.get("strain_score"),
            "power_hr_ratio": a.get("icu_power_hr"),
            # Pace & form
            "average_speed": calculate_speed(a.get("average_speed"), a.get("type")),
            "average_cadence": a.get("average_cadence"),
            # Workout structure
            "interval_summary": (
                a.get("interval_summary")
                if a.get("type") != "Swim"
                else parse_interval_summary(a.get("interval_summary"))
            ),
            # Body & fuel
            "calories": a.get("calories"),
        }
        for a in strip_empty(response)
    ]
    return strip_empty(data)


def get_wellness(past, raw=False):
    oldest, newest = get_date_range(past)
    response = api_get("wellness", params={"oldest": oldest, "newest": newest})
    if raw:
        return response
    data = [
        {
            "date": w.get("id"),
            "ctl": w.get("ctl"),
            "atl": w.get("atl"),
            "ramp_rate": w.get("rampRate"),
            "resting_hr": w.get("restingHR"),
            "hrv": w.get("hrv"),
            "sleep_hours": seconds_to_hhmmss(w.get("sleepSecs")),
            "sleep_score": w.get("sleepScore"),
        }
        for w in strip_empty(response)
    ]
    return strip_empty(data)


def get_athlete():
    if not ATHLETE_FILE.exists():
        raise FileNotFoundError(
            "Missing .athlete file. Copy .athlete.example to .athlete and fill it in."
        )
    with open(ATHLETE_FILE) as f:
        return load(f)


def get_events(past="6mo", future="6mo", raw=False):
    """Fetch planned events / races."""
    oldest, newest = get_date_range(past, future=future)
    ret = api_get("events", params={"oldest": oldest, "newest": newest})
    if raw:
        return ret
    # filter for races only
    return [
        {
            "name": e.get("name"),
            "date": e.get("start_date_local")[:10],
            "category": e.get("category"),
            "type": (e.get("type") if e.get("type") != "Other" else "Triathlon"),
            "description": e.get("description"),
        }
        for e in ret
        if e.get("category").startswith("RACE")
    ]


def build_training_summary(past="42d"):
    return {
        "window": past,
        "athlete": get_athlete(),
        "wellness": get_wellness(past),
        "activities": get_activities(past),
        "events": get_events(),
    }
