<img width="1470" height="923" alt="SCR-20260406-pupr" src="https://github.com/user-attachments/assets/756661fb-339f-48e0-91d8-9e494dd0acb8" />

# triclops

An AI triathlon coach powered by Claude and [Intervals.icu](https://intervals.icu).

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
```

### Environment variables

Copy the example and fill in your keys:

```sh
cp .env.example .env
```

| Variable               | Description                                               |
| ---------------------- | --------------------------------------------------------- |
| `INTERVALS_ATHLETE_ID` | Your Intervals.icu athlete ID (found in your profile URL) |
| `INTERVALS_API_KEY`    | Intervals.icu API key (Settings > Developer)              |
| `ANTHROPIC_API_KEY`    | Anthropic API key                                         |

### Athlete profile

Copy the example and fill in your details:

```sh
cp .athlete.example .athlete
```

## Run

```sh
./run.sh
```

The app will be available at `http://localhost:5050`.

## Tips

- By default, the app uses a 42-day window of activity and wellness data from your Intervals.icu to use as context for its responses. It also has access to upcoming races within the next 6 months.
- Conversations are not persisted because the app is intended for periodic check-ins. This allows it to always provide advice based on your most recent data. However, the "Export" button will save the current conversation under `conversations/` as a markdown file.
- If `training_plan.txt` exists, it will be used as additional context for responses.
