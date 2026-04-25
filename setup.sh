#!/bin/bash
set -e

echo "============================================"
echo " TKD Tournament Apps - Auto Setup (Mac)"
echo "============================================"
echo ""

# ── uv (Python package manager, no admin needed) ─────────────────────────────
if ! command -v uv &> /dev/null && [ ! -f "$HOME/.local/bin/uv" ]; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo ""
fi
export PATH="$HOME/.local/bin:$PATH"

# ── Python (via uv, no admin needed) ─────────────────────────────────────────
echo "Checking Python..."
uv python install 3.12
echo ""

# ── nvm + Node.js (no admin needed) ──────────────────────────────────────────
export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    echo "Installing nvm (Node version manager)..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    echo ""
fi
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    nvm install --lts
    echo ""
fi

# ── Git check ────────────────────────────────────────────────────────────────
if ! command -v git &> /dev/null; then
    echo "Git not found. Run this command first, then re-run setup:"
    echo ""
    echo "  xcode-select --install"
    echo ""
    echo "A popup will appear — click Install and wait for it to finish."
    exit 1
fi

# ── Clone / update tkd_bracket_system ────────────────────────────────────────
TKD="$HOME/Desktop/tkd_bracket_system"
if [ ! -f "$TKD/app.py" ]; then
    rm -rf "$TKD"
    echo "Downloading TKD Bracket System..."
    git clone https://github.com/MichaelNguyenz229/tkd_bracket_system.git "$TKD"
    echo ""
else
    echo "Updating TKD Bracket System..."
    git -C "$TKD" pull --ff-only
    echo ""
fi

# ── Install Python app dependencies ──────────────────────────────────────────
echo "Installing Python app dependencies..."
cd "$TKD"
uv sync
echo ""

# ── Clone / update bracket_generator ─────────────────────────────────────────
BG="$HOME/Desktop/bracket_generator"
if [ ! -f "$BG/package.json" ]; then
    rm -rf "$BG"
    echo "Downloading Bracket Generator..."
    git clone https://github.com/MichaelNguyenz229/bracket-generator.git "$BG"
    echo ""
else
    echo "Updating Bracket Generator..."
    git -C "$BG" pull --ff-only
    echo ""
fi

# ── Install bracket generator dependencies ────────────────────────────────────
echo "Installing Bracket Generator dependencies..."
cd "$BG"
npm install
echo ""

# ── Create double-clickable Desktop shortcuts ─────────────────────────────────
cat > "$HOME/Desktop/Launch Bracket Generator.command" << 'CMD'
#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/Desktop/bracket_generator"
sleep 2 && open http://localhost:5173 &
npm run dev
CMD
chmod +x "$HOME/Desktop/Launch Bracket Generator.command"

cat > "$HOME/Desktop/Launch TKD App.command" << 'CMD'
#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/Desktop/tkd_bracket_system"
sleep 2 && open http://localhost:8501 &
uv run streamlit run app.py
CMD
chmod +x "$HOME/Desktop/Launch TKD App.command"

echo "============================================"
echo " Setup complete!"
echo "============================================"
echo ""
echo "Two shortcuts are on your Desktop:"
echo "  - 'Launch TKD App.command'"
echo "  - 'Launch Bracket Generator.command'"
echo ""
echo "Double-click either one to open the app."
echo ""
echo "Starting TKD Pipeline app now..."
echo ""
cd "$TKD"
sleep 2 && open http://localhost:8501 &
uv run streamlit run app.py
