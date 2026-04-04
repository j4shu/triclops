import json
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

import anthropic
from intervals_client import build_training_summary

load_dotenv()

app = Flask(__name__)

SYSTEM_PROMPT = """You are an expert triathlon coach and sports scientist analyzing an age-group triathlete's training data from Intervals.icu. You have deep knowledge of:
- Periodization and training load management (CTL/ATL/TSB)
- Swim/bike/run training principles
- Heart rate and power-based training zones
- Recovery, fatigue management, and injury prevention
- Race preparation, tapering, and pacing strategy
- Nutrition and weight management for endurance athletes

When the athlete asks a question, analyze their provided training data carefully.
Be specific with numbers and trends from their data. Reference specific workouts or dates when relevant.
Give actionable, practical advice. Be honest about concerns (overtraining, insufficient volume, etc.).
Keep responses focused and conversational — this is a chat, not a report.

If the data is insufficient to answer a question, say so and explain what additional data would help."""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json()
    user_message = body.get("message", "").strip()
    window = body.get("window", "42d")
    history = body.get("history", [])

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Fetch training data
    try:
        summary = build_training_summary(window)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch Intervals.icu data: {e}"}), 502

    # Build the data context message
    data_context = (
        f"Here is the athlete's training data for the last {window} window:\n\n"
        f"```json\n{json.dumps(summary, indent=2, default=str)}\n```"
    )

    # Build messages for Claude
    messages = []

    # Include conversation history
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message with data context
    full_user_message = f"{data_context}\n\nAthlete's question: {user_message}"
    messages.append({"role": "user", "content": full_user_message})

    # Call Claude
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = response.content[0].text
    except Exception as e:
        return jsonify({"error": f"Claude API error: {e}"}), 502

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True, port=5050)
