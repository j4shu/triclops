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
            "is_race": a.get("sub_type"),
            # Duration & distance
            "duration": a.get("moving_time", a.get("elapsed_time")),
            "distance": a.get("distance"),
            # Training load & fitness
            "training_load": a.get("icu_training_load"),
            "intensity": a.get("icu_intensity"),
            "ctl": round(a.get("icu_ctl"), 2),
            "atl": round(a.get("icu_atl"), 2),
            "tsb": round(a.get("icu_ctl") - a.get("icu_atl"), 2),
            "trimp": round(a.get("trimp"), 2),
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
            "strain_score": a.get("strain_score"),
            "work": a.get("icu_joules"),
            # Pace & form
            "average_speed": a.get("average_speed"),
            "average_cadence": a.get("average_cadence"),
            # Workout structure
            "interval_summary": a.get("interval_summary"),
            # Body & fuel
            "calories": a.get("calories"),
        }
        for a in response
    ]
    data = strip_empty(data)
    for d in data:
        d["duration"] = seconds_to_hhmmss(d.get("duration"))
        type = d.get("type")
        # activity specific fields
        if type == "Swim":
            d["distance"] = meters_to_yards(d.get("distance"))
            d["average_speed"] = mps_to_min_per_100yds(d.get("average_speed"))
            d["interval_summary"] = parse_swim_interval_summary(
                d.get("interval_summary")
            )
        elif type == "Run":
            d["average_speed"] = mps_to_min_per_mile(d.get("average_speed"))
        else:
            # some activities don't have these
            if d.get("distance"):
                d["distance"] = meters_to_miles(d.get("distance"))
            if d.get("average_speed"):
                d["average_speed"] = mps_to_mph(d.get("average_speed"))
        # misc fields
        if d.get("work"):
            d["work"] = f"{round(d.get('work') / 1000, 2)}kJ"
        if d.get("is_race") == "RACE":
            d["is_race"] = True
    data.sort(key=lambda x: x.get("date"), reverse=True)
    return data


def get_wellness(past, raw=False):
    oldest, newest = get_date_range(past)
    response = api_get("wellness", params={"oldest": oldest, "newest": newest})
    if raw:
        return response
    data = [
        {
            "date": w.get("id"),
            "ctl": round(w.get("ctl"), 2),
            "atl": round(w.get("atl"), 2),
            "tsb": round(w.get("ctl") - w.get("atl"), 2),
            "ramp_rate": round(w.get("rampRate"), 2),
            "resting_hr": w.get("restingHR"),
            "hrv": w.get("hrv"),
            "sleep_hours": w.get("sleepSecs"),
            "sleep_score": w.get("sleepScore"),
        }
        for w in response
    ]
    data = strip_empty(data)
    for d in data:
        if d.get("sleep_hours"):
            d["sleep_hours"] = seconds_to_hhmmss(d["sleep_hours"])
    data.sort(key=lambda x: x.get("date"), reverse=True)
    return data


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
    data = [
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
    data.sort(key=lambda x: x.get("date"))
    return data


def build_training_summary(past="42d"):
    return {
        "window": past,
        "athlete": get_athlete(),
        "wellness": get_wellness(past),
        "activities": get_activities(past),
        "events": get_events(),
    }
