#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")"
echo "Launching TKD Bracket App..."
echo "The app will open in your browser at http://localhost:8501"
echo "Keep this window open. Press Ctrl+C to stop."
echo ""
uv run streamlit run app.py
