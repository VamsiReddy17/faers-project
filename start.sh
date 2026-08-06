#!/bin/bash
# =============================================================
# FAERS Pipeline — START
# =============================================================
# Activates the virtual environment, runs the full pipeline,
# and launches the Streamlit dashboard.
# =============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  FAERS PHARMACOVIGILANCE PIPELINE — STARTING            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ---- Activate virtual environment ----
if [ -d "venv" ]; then
    echo "✓ Activating virtual environment..."
    source venv/bin/activate
else
    echo "✗ Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# ---- Run the data pipeline (if processed data doesn't exist) ----
if [ ! -f "data/processed/signal_results.csv" ] || [ "$1" == "--force-ingest" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Step 1: Running data pipeline (ingestion → analysis)..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    python -m src.main
else
    echo "✓ Processed dataset ready in data/processed/"
fi

# ---- Launch Streamlit dashboard ----
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 2: Launching Streamlit dashboard..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Save the PID so stop.sh can kill it
streamlit run dashboard/app.py --server.port 8501 &
STREAMLIT_PID=$!
echo "$STREAMLIT_PID" > .streamlit_pid

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✓ PIPELINE COMPLETE                                    ║"
echo "║                                                          ║"
echo "║  Dashboard running at: http://localhost:8501              ║"
echo "║  Streamlit PID: $STREAMLIT_PID"
echo "║                                                          ║"
echo "║  Run ./stop.sh to stop the dashboard.                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Wait for Streamlit to keep the script alive
wait $STREAMLIT_PID
