from json import dumps
from datetime import datetime
from pathlib import Path

import anthropic
import gradio as gr
from dotenv import load_dotenv

from intervals_client import build_training_summary

load_dotenv()

CONVERSATIONS_DIR = Path("conversations")
CONVERSATIONS_DIR.mkdir(exist_ok=True)

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


def save_conversation(history, last_user_msg, last_reply, window):
    """Auto-save the full conversation to a markdown file in conversations/."""
    all_msgs = list(history) + [
        {"role": "user", "content": last_user_msg},
        {"role": "assistant", "content": last_reply},
    ]
    # Use a stable filename based on the first message timestamp
    # so follow-up messages update the same file
    if len(all_msgs) <= 2:
        # New conversation — create a new file
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"chat_{ts}.md"
    else:
        # Continuing conversation — find the most recent file and overwrite
        existing = sorted(CONVERSATIONS_DIR.glob("chat_*.md"))
        filename = (
            existing[-1].name
            if existing
            else f"chat_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.md"
        )

    md = f"# Training Analysis Conversation\n"
    md += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    md += f"**Data window:** {window}\n\n---\n\n"
    for msg in all_msgs:
        label = "## You" if msg["role"] == "user" else "## Claude"
        md += f"{label}\n\n{msg['content']}\n\n"

    (CONVERSATIONS_DIR / filename).write_text(md)


WINDOW_CHOICES = [
    ("7 days", "7d"),
    ("1 month", "1mo"),
    ("42 days", "42d"),
    ("3 months", "3mo"),
    ("6 months", "6mo"),
    ("1 year", "1y"),
]


def respond(message, history, window):
    """Stream a response from Claude with Intervals.icu data context."""
    # Build Claude messages — inject data context only on first turn
    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    if not history:
        try:
            summary = build_training_summary(window)
        except Exception as e:
            yield f"**Error fetching Intervals.icu data:** {e}"
            return
        data_context = (
            f"Here is the athlete's training data for the last {window} window:\n\n"
            f"```json\n{dumps(summary, indent=2, default=str)}\n```\n\n"
        )
        # reference training plan if it exists
        training_plan_path = CONVERSATIONS_DIR / "training_plan.txt"
        if training_plan_path.exists():
            plan_text = training_plan_path.read_text().strip()
            data_context += (
                f"Here is the athlete's current training plan. Use this as a reference "
                f"to check whether their recent activity data lines up with what was "
                f"prescribed:\n\n```\n{plan_text}\n```\n\n"
                f"When making changes or recommendations, output the workouts in the "
                f"same format as the training plan for consistency and clarity.\n\n"
            )
        full_message = f"{data_context}Athlete's question: {message}"
    else:
        full_message = message

    messages.append({"role": "user", "content": full_message})

    # Stream from Claude
    client = anthropic.Anthropic()
    reply = ""
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=16384,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            reply += text
            yield reply

    # Auto-save conversation
    save_conversation(history, message, reply, window)


EXAMPLES = [
    ["Create a training plan up until my next race based on my recent training data."],
    ["Give me a summary of my recent training and key areas to improve."],
    ["How has my training load been trending? Am I at risk of overtraining?"],
    ["Break down my swim/bike/run volume distribution. Is it balanced?"],
]

with gr.Blocks(
    title="triclops",
) as app:
    gr.Markdown(
        "# triclops: An AI Triathlon Coach\n"
        "*One eye on your swim. One on your bike. One on your run.*"
    )

    window = gr.Dropdown(
        choices=WINDOW_CHOICES,
        value="42d",
        label="Data Window",
    )

    gr.ChatInterface(
        fn=respond,
        additional_inputs=[window],
        examples=EXAMPLES,
    )

if __name__ == "__main__":
    app.launch(
        server_port=5050,
        theme=gr.themes.Glass(
            spacing_size="lg",
            text_size="lg",
            font=[gr.themes.GoogleFont("MesloLGM Nerd Font")],
        ),
    )
