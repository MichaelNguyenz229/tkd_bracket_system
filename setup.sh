#!/bin/bash
set -e

echo "============================================"
echo " TKD Bracket App - Auto Setup (Mac)"
echo "============================================"
echo ""

# Install Homebrew if missing
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for Apple Silicon Macs
    if [[ $(uname -m) == "arm64" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    echo ""
fi

# Install Git if missing
if ! command -v git &> /dev/null; then
    echo "Installing Git..."
    brew install git
    echo ""
fi

# Install Python if missing
if ! command -v python3 &> /dev/null; then
    echo "Installing Python..."
    brew install python@3.12
    echo ""
fi

# Clone repo to Desktop if not already done
DEST="$HOME/Desktop/tkd_bracket_system"
if [ ! -d "$DEST" ]; then
    echo "Downloading app to Desktop..."
    git clone https://github.com/MichaelNguyenz229/tkd_bracket_system.git "$DEST"
    echo ""
fi

cd "$DEST"

# Install uv if missing
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo ""
fi

export PATH="$HOME/.local/bin:$PATH"

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
