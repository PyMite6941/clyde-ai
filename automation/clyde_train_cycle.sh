#!/bash/bash
# Clyde training cycle — runs a single pack
set -e

CLYDE_DIR="/home/pymite6941/Clyde"
STATUS_FILE="$CLYDE_DIR/automation/training_status.json"
NOTEBOOK="anthropic_student_baseline.ipynb"

# Parse arguments
PACK="english"
TRACK="A"
RESUME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --pack) PACK="$2"; shift 2 ;;
        --track) TRACK="$2"; shift 2 ;;
        --resume) RESUME="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Generate run name with timestamp
DATE_SUFFIX=$(date +%Y%m%d_%H%M%S)
RUN_NAME="${TRACK}-${PACK}-${DATE_SUFFIX}"

# Check if resuming
if [ -n "$RESUME" ]; then
    RESUME_FROM_ARG="RESUME_FROM=$RESUME"
else
    RESUME_FROM_ARG="RESUME_FROM=None"
fi

echo "=== CLYDE TRAINING CYCLE ==="
echo "Run: $RUN_NAME"
echo "Pack: $PACK"
echo "Track: $TRACK"
echo "Resume from: $RESUME"

echo ""
echo "=== KAGGLE NOTEBOOK SETUP REQUIRED ==="
echo "Please do the following in your Kaggle session:"
echo "1. Ensure dataset 'clyde-training-data' is attached (Settings -> Add data)"
echo "2. In the notebook Cell 1, edit these variables:"
echo "   TRACK = "$TRACK""
echo "   DATA_PACK = "$PACK""
echo "   RUN_NAME = "$RUN_NAME""
echo "   RESUME_FROM = $RESUME_FROM_ARG"
echo ""
echo "3. Run all cells (0 through 11)"
echo "4. Save Version with output (crucial!)"
echo ""
echo "=== AFTER RUN COMPLETES ==="
echo "Run this to update status:"
echo "  python3 -c "import json, time; status = json.load(open('$STATUS_FILE')); status['current_run'] = None; json.dump(status, open('$STATUS_FILE', 'w'), indent=2); print('Status cleared')""
echo ""
echo "=== DONE ==="
echo "Check status: cat $STATUS_FILE"
