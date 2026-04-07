#!/bin/bash
lsof -ti:5050 | xargs kill 2>/dev/null
uv run gradio app.py
