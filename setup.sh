#!/bin/bash
set -e

echo "============================================"
echo " TKD Bracket App - Auto Setup (Mac)"
echo "============================================"
echo ""

# Install uv (no admin needed, installs to ~/.local/bin)
if ! command -v uv &> /dev/null && [ ! -f "$HOME/.local/bin/uv" ]; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo ""
fi

export PATH="$HOME/.local/bin:$PATH"

# Use uv to install Python (no admin needed)
echo "Checking Python..."
uv python install 3.12
echo ""

# Check for git
if ! command -v git &> /dev/null; then
    echo "Git not found. Run this command first, then re-run setup:"
    echo ""
    echo "  xcode-select --install"
    echo ""
    echo "A popup will appear — click Install and wait for it to finish."
    exit 1
fi

# Clone repo to Desktop
DEST="$HOME/Desktop/tkd_bracket_system"
if [ ! -d "$DEST" ]; then
    echo "Downloading app to Desktop..."
    git clone https://github.com/MichaelNguyenz229/tkd_bracket_system.git "$DEST"
    echo ""
fi

cd "$DEST"

# Install app dependencies
echo "Installing app dependencies..."
uv sync

echo ""
echo "============================================"
echo " Setup complete! Launching app..."
echo "============================================"
echo ""
echo "The app will open in your browser at http://localhost:8501"
echo "Keep this window open while using the app."
echo "Press Ctrl+C to stop the app."
echo ""
uv run streamlit run app.py
