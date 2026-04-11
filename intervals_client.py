from datetime import datetime
from json import dump, load
from pathlib import Path

from helpers import *

ATHLETE_FILE = Path(".athlete")
CACHE_FILE = Path(".cache/training_summary.json")


def _load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return load(f)
    return {}


def _save_cache(data):
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        dump(data, f, indent=2, default=str)


def get_activities(oldest, newest):
    response = api_get_athlete(
        "activities", params={"oldest": oldest, "newest": newest}
    )

    data = {}
    for a in response:
        date = a.get("start_date_local", "")[:10]
        if data.get(date) is None:
            data[date] = {"activities": []}

        activity_data = {
            # Identity
            "type": a.get("type"),
            "name": a.get("name"),
            "is_race": a.get("sub_type"),
            # Duration & distance
            "duration": seconds_to_hhmmss(a.get("moving_time", a.get("elapsed_time"))),
            "distance": a.get("distance"),
            # Training load & fitness
            "training_load": a.get("icu_training_load"),
            "intensity": a.get("icu_intensity"),
            # "ctl": round(a.get("icu_ctl"), 2),
            # "atl": round(a.get("icu_atl"), 2),
            # "tsb": round(a.get("icu_ctl") - a.get("icu_atl"), 2),
            # "trimp": round(a.get("trimp"), 2),
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
        }
        # process activity specific fields
        type = activity_data["type"]
        if type == "Swim":
            activity_data["distance"] = meters_to_yards(activity_data.get("distance"))
            activity_data["average_speed"] = mps_to_min_per_100yds(
                activity_data.get("average_speed")
            )
            activity_data["interval_summary"] = parse_swim_interval_summary(
                activity_data.get("interval_summary")
            )
        elif type == "Run":
            activity_data["average_speed"] = mps_to_min_per_mile(
                activity_data.get("average_speed")
            )
        elif type in ["VirtualRide", "Ride"]:
            activity_data["distance"] = meters_to_miles(activity_data.get("distance"))
            activity_data["average_speed"] = mps_to_mph(
                activity_data.get("average_speed")
            )
            # activity_data["work"] = f"{round(activity_data.get('work') / 1000, 2)}kJ"
        # misc fields
        if activity_data.get("is_race") == "RACE":
            activity_data["is_race"] = True

        # process intervals data
        interval_details = api_get_activity_intervals(a.get("id")).get("icu_intervals")
        if interval_details:
            new_interval_details = []
            if type == "Swim":
                for i in interval_details:
                    new_interval = {}
                    if i.get("distance"):
                        new_interval["distance"] = meters_to_yards(i.get("distance"))
                    if i.get("elapsed_time"):
                        new_interval["duration"] = seconds_to_hhmmss(
                            i.get("elapsed_time")
                        )
                    if i.get("zone"):
                        new_interval["zone"] = i.get("zone")
                    if i.get("average_speed"):
                        new_interval["average_speed"] = mps_to_min_per_100yds(
                            i.get("average_speed")
                        )
                    if i.get("average_heartrate"):
                        new_interval["average_heartrate"] = i.get("average_heartrate")
                    if i.get("type"):
                        new_interval["type"] = i.get("type")
                    new_interval_details.append(new_interval)
            elif type in ["Run", "VirtualRun"]:
                for i in interval_details:
                    new_interval = {}
                    if i.get("distance"):
                        new_interval["distance"] = meters_to_miles(i.get("distance"))
                    if i.get("elapsed_time"):
                        new_interval["duration"] = seconds_to_hhmmss(
                            i.get("elapsed_time")
                        )
                    if i.get("zone"):
                        new_interval["zone"] = i.get("zone")
                    if i.get("average_speed"):
                        new_interval["average_speed"] = mps_to_min_per_mile(
                            i.get("average_speed")
                        )
                    if i.get("grade_adjusted_speed"):
                        new_interval["grade_adjusted_speed"] = mps_to_min_per_mile(
                            i.get("grade_adjusted_speed")
                        )
                    if i.get("average_heartrate"):
                        new_interval["average_heartrate"] = i.get("average_heartrate")
                    if i.get("type"):
                        new_interval["type"] = i.get("type")
                    new_interval_details.append(new_interval)
            elif type in ["VirtualRide", "Ride"]:
                for i in interval_details:
                    new_interval = {}
                    if i.get("distance"):
                        new_interval["distance"] = meters_to_miles(i.get("distance"))
                    if i.get("elapsed_time"):
                        new_interval["duration"] = seconds_to_hhmmss(
                            i.get("elapsed_time")
                        )
                    if i.get("average_watts"):
                        new_interval["average_watts"] = i.get("average_watts")
                    if i.get("decoupling"):
                        new_interval["decoupling"] = i.get("decoupling")
                    if i.get("zone"):
                        new_interval["zone"] = i.get("zone")
                    if i.get("average_speed"):
                        new_interval["average_speed"] = mps_to_mph(
                            i.get("average_speed")
                        )
                    if i.get("average_heartrate"):
                        new_interval["average_heartrate"] = i.get("average_heartrate")
                    if i.get("type"):
                        new_interval["type"] = i.get("type")
                    new_interval_details.append(new_interval)
            activity_data["interval_details"] = new_interval_details

        # append activity data to the correct date
        data[date]["activities"].append(activity_data)

    data = strip_empty(data)
    return data


def get_wellness(oldest, newest):
    response = api_get_athlete("wellness", params={"oldest": oldest, "newest": newest})
    data = {
        w.get("id"): {
            "wellness": {
                "ctl": round(w.get("ctl"), 2),
                "atl": round(w.get("atl"), 2),
                "tsb": round(w.get("ctl") - w.get("atl"), 2),
                "ramp_rate": round(w.get("rampRate"), 2),
                "resting_hr": w.get("restingHR"),
                "hrv": w.get("hrv"),
                "sleep_hours": seconds_to_hhmmss(w.get("sleepSecs")),
                "sleep_score": w.get("sleepScore"),
            }
        }
        for w in response
    }
    data = strip_empty(data)
    return data


def get_athlete():
    if not ATHLETE_FILE.exists():
        raise FileNotFoundError(
            "Missing .athlete file. Copy .athlete.example to .athlete and fill it in."
        )
    with open(ATHLETE_FILE) as f:
        return load(f)


def get_events():
    oldest, newest = get_date_bounds(past=180, future=180)
    ret = api_get_athlete("events", params={"oldest": oldest, "newest": newest})
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


def build_training_summary(past, force=False):
    today = datetime.now().date().isoformat()
    requested_dates = get_date_range(past)

    cache = _load_cache()
    # set intersection: find which dates are already in the cache
    cached_dates = set(cache.keys()) & requested_dates

    # finds dates not in the cache, but always include today (union)
    missing_dates = (requested_dates - cached_dates) | {today}
    if force:
        missing_dates = requested_dates

    if missing_dates:
        """
        Find the earliest and latest missing dates to form the API query range.
        This means if you're missing days 1, 3, and 5, it fetches the range 1-5
        (which may re-fetch days 2 and 4 — that's fine, they just overwrite).
        """
        fetch_oldest = min(missing_dates)
        fetch_newest = max(missing_dates)

        wellness = get_wellness(oldest=fetch_oldest, newest=fetch_newest)
        activities = get_activities(oldest=fetch_oldest, newest=fetch_newest)
        for date in wellness.keys() | activities.keys():
            cache[date] = {
                **(wellness.get(date, {})),
                **(activities.get(date, {})),
            }

        # prune cache to the last 365 days to prevent unbounded growth
        cutoff = get_date_bounds(365)[0]
        cache = {d: v for d, v in sorted(cache.items(), reverse=True) if d >= cutoff}
        _save_cache(cache)

    # Return only dates in the requested window
    combined = {date: cache[date] for date in requested_dates if date in cache}

    return {
        "past_days": past,
        "dates": combined,
        "events": get_events(),
    }
