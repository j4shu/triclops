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


WINDOW_CHOICES = [
    ("7 days", "7d"),
    ("1 month", "1mo"),
    ("42 days", "42d"),
    ("3 months", "3mo"),
    ("6 months", "6mo"),
    ("1 year", "1y"),
]

EXAMPLES = [
    ["Create a training plan up until my next race based on my recent training data."],
    ["Give me a summary of my recent training and key areas to improve."],
    ["How has my training load been trending? Am I at risk of overtraining?"],
    ["Break down my swim/bike/run volume distribution. Is it balanced?"],
]


def export_conversation(history, window):
    """Export the conversation to a markdown file in conversations/."""
    if not history:
        gr.Info("No conversation to export.")
        return
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"chat_{ts}.md"
    md = f"# Training Analysis Conversation\n"
    md += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    md += f"**Data window:** {window}\n\n---\n\n"
    for msg in history:
        label = "## You" if msg["role"] == "user" else "## Claude"
        content = msg["content"]
        if isinstance(content, list):
            content = "\n".join(block["text"] for block in content if block.get("text"))
        md += f"{label}\n\n{content}\n\n"
    (CONVERSATIONS_DIR / filename).write_text(md)
    gr.Info(f"Conversation exported to {filename}")


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

    chatbot = gr.Chatbot(
        height="75vh", show_label=False, resizable=True, autoscroll=False
    )
    textbox = gr.Textbox()
    gr.ChatInterface(
        fn=respond,
        additional_inputs=[window],
        examples=EXAMPLES,
        chatbot=chatbot,
        textbox=textbox,
    )

    export_btn = gr.Button("Export", variant="primary", size="md", scale=0)
    export_btn.click(fn=export_conversation, inputs=[chatbot, window])

if __name__ == "__main__":
    app.launch(
        server_port=5050,
        theme=gr.themes.Glass(font=[gr.themes.GoogleFont("MesloLGM Nerd Font")]),
    )
