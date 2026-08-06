#!/bin/bash
# =============================================================
# FAERS Pipeline — STOP
# =============================================================
# Stops the running Streamlit dashboard and any pipeline processes.
# =============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  FAERS PHARMACOVIGILANCE PIPELINE — STOPPING            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

STOPPED=0

# ---- Stop Streamlit via saved PID ----
if [ -f ".streamlit_pid" ]; then
    PID=$(cat .streamlit_pid)
    if kill -0 "$PID" 2>/dev/null; then
        echo "  Stopping Streamlit dashboard (PID: $PID)..."
        kill "$PID"
        sleep 1
        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            echo "  Force stopping (PID: $PID)..."
            kill -9 "$PID"
        fi
        echo "  ✓ Streamlit stopped."
        STOPPED=1
    else
        echo "  Streamlit process (PID: $PID) is not running."
    fi
    rm -f .streamlit_pid
fi

# ---- Kill any remaining Streamlit processes for this project ----
STREAMLIT_PIDS=$(pgrep -f "streamlit run dashboard/app.py" 2>/dev/null)
if [ -n "$STREAMLIT_PIDS" ]; then
    echo "  Stopping additional Streamlit processes: $STREAMLIT_PIDS"
    echo "$STREAMLIT_PIDS" | xargs kill 2>/dev/null
    sleep 1
    echo "$STREAMLIT_PIDS" | xargs kill -9 2>/dev/null
    echo "  ✓ All Streamlit processes stopped."
    STOPPED=1
fi

# ---- Kill any running pipeline processes ----
PIPELINE_PIDS=$(pgrep -f "python -m src.main" 2>/dev/null)
if [ -n "$PIPELINE_PIDS" ]; then
    echo "  Stopping pipeline processes: $PIPELINE_PIDS"
    echo "$PIPELINE_PIDS" | xargs kill 2>/dev/null
    sleep 1
    echo "  ✓ Pipeline processes stopped."
    STOPPED=1
fi

if [ "$STOPPED" -eq 0 ]; then
    echo "  No running FAERS processes found."
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✓ ALL PROCESSES STOPPED                                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
