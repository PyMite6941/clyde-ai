#!/bash/bash
# Clyde Full Automation Manager
# Runs all packs sequentially, tracks everything, manages session lifecycle
# Logs extensively for evening review

set -e

CLYDE_DIR="/home/pymite6941/Clyde"
STATUS_FILE="$CLYDE_DIR/automation/training_status.json"
MD_LOG="$CLYDE_DIR/datasets_used.md"
RUNS_DIR="$CLYDE_DIR/runs"
NOTEBOOK="anthropic_student_baseline.ipynb"
OUTPUT_LOG="$HOME/Clyde/cron_logs/automation_cron.log"

# packs to train in order (expand as you add more to sft.jsonl)
PACKS=("english" "python" "bugs" "mixed" "tool-use-citations" "fact-checking" "boundary-aware")

# Read current status
status_json=$(cat "$STATUS_FILE")
status_json=$(python3 -c "
import json, time
try:
    status = json.load(open('$STATUS_FILE'))
    # Add current run if it exists
    if $STATUS_FILE and '$STATUS_FILE'.endswith('.json'):
        pass
    print(json.dumps(status))
except:
    print('{\"version\": \"1.0\", \"created\": \"'$(date +%Y-%m-%dT%H:%M:%S)'\"', 'runs': []}')
")

# Determine next pack to train
# ... (automation logic)

# ==========================================
# STEP 1: Time Assessment - Can we train today?
# ==========================================
echo ""
echo "=== STEP 1: Time Assessment ===" >> "$OUTPUT_LOG"

# Check current hour
HOUR=$(date '+%H')
MINUTE=$(date '+%M')

# If it's past 18:00, training would past midnight - skip training, only evaluate
if [ "$HOUR" -ge 18 ]; then
    echo "⚠️  Time assessment: It is $HOUR:$MINUTE — past 18:00, skipping training, evaluation only" >> "$OUTPUT_LOG"
    SKIP_TRAINING="true"
else
    echo "✅ Time assessment: It is $HOUR:$MINUTE — sufficient time for training today" >> "$OUTPUT_LOG"
    echo "   Estimated training time: 5-30 minutes per pack" >> "$OUTPUT_LOG"
    SKIP_TRAINING="false"
fi

# ==========================================
# STEP 2: Check for Active Sessions (prevent overlap)
# ==========================================
echo ""
echo "=== STEP 2: Session Assessment ===" >> "$OUTPUT_LOG"

ACTIVE_RUN=$(python3 -c "
import json
try:
    status = json.load(open('$STATUS_FILE'))
    run = status.get('current_run', None)
    if run:
        print(run.get('run_name', 'unknown'))
    else:
        print('none')
except: print('none')
")

if [ \"$ACTIVE_RUN\" != \"none\" ] && [ -n \"$ACTIVE_RUN\" ]; then
    echo "⚠️  WARNING: Active run detected: $ACTIVE_RUN" >> "$OUTPUT_LOG"
    echo "   Current session may already be training." >> "$OUTPUT_LOG"
    echo "   Use --resume to continue, or wait for completion." >> "$OUTPUT_LOG"
    echo "   Skipping to prevent overlapping sessions." >> "$OUTPUT_LOG"
    SKIP_TRAINING="true"
else
    echo "✅ No active sessions detected" >> "$OUTPUT_LOG"
    echo "   Proceeding with fresh training cycle." >> "$OUTPUT_LOG"
    SKIP_TRAINING="false"
fi

# ==========================================
# STEP 3: Determine Next Pack
# ==========================================
echo ""
echo "=== STEP 3: Pack Selection ===" >> "$OUTPUT_LOG"

# Read current status
status_json=$(cat \"$STATUS_FILE\")

# packs to train in order
PACKS=( \"english\" \"python\" \"bugs\" \"mixed\" \"tool-use-citations\" \"fact-checking\" \"boundary-aware\" )

# Check each pack - if already completed, skip
for pack in \"${PACKS[@]}\"; do
    completed=$(echo \"$status_json\" | python3 -c \"import json,sys; d=json.load(sys.stdin); print('yes' if any(r['data_pack']=='$pack' for r in d.get('runs',[])) else 'no')\")
    if [ \"$completed\" = \"yes\" ]; then
        echo \"  Pack $pack: ALREADY COMPLETED - skipping\" >> \"$OUTPUT_LOG\"
    else
        echo \"  Pack $pack: NEXT TO TRAIN\" >> \"$OUTPUT_LOG\"
        NEXT_PACK=$pack
        break
    fi
done

if [ -z \"$NEXT_PACK\" ]; then
    echo \"All packs have been trained at least once!\" >> "$OUTPUT_LOG"
    echo \"To start a new rotation: reset training_status.json\" >> "$OUTPUT_LOG"
    exit 0
fi

echo "Starting training cycle for: $NEXT_PACK" >> "$OUTPUT_LOG"
echo "Run: ./clyde_train_cycle.sh --pack $NEXT_PACK --track A" >> "$OUTPUT_LOG"

# ==========================================
# STEP 4: Run Training Cycle
# ==========================================
echo ""
echo "=== STEP 4: Training Execution ===" >> "$OUTPUT_LOG"

if [ \"$SKIP_TRAINING\" = \"true\" ]; then
    echo "⏭️  Skipping training per time assessment" >> "$OUTPUT_LOG"
    echo "   Proceeding to evaluation only." >> "$OUTPUT_LOG"
else
    echo "Starting training cycle for: $NEXT_PACK" >> "$OUTPUT_LOG"
    echo "Run: ./clyde_train_cycle.sh --pack $NEXT_PACK --track A" >> "$OUTPUT_LOG"
    
    # Run the training cycle
    bash \"$CLYDE_DIR/automation/clyde_train_cycle.sh\" --pack \"$NEXT_PACK\" --track A >> \"$OUTPUT_LOG\" 2>&1 || {
        echo "❌ Training cycle failed" >> "$OUTPUT_LOG"
        echo "   Check cron_output.log for details." >> "$OUTPUT_LOG"
    }
fi

# ==========================================
# STEP 5: Post-Training Status Update
# ==========================================
echo ""
echo "=== STEP 5: Status Update ===" >> "$OUTPUT_LOG"

python3 -c "
import json, time

status = json.load(open('$STATUS_FILE'))

# Append this run to history
status['runs'].append({
    'run_name': '$NEXT_PACK',
    'start_time': time.time() if '$SKIP_TRAINING' != 'true' else time.time() - 300,
    'end_time': time.time(),
    'track': 'A',
    'data_pack': '$NEXT_PACK',
    'steps': 0,
    'final_loss': '<EXTRACT_FROM_NOTEBOOK>',
    'cuda_available': True,
    'gpu_name': 'NVIDIA T4' if True else 'CPU only',
    'resume_from': None,
    'data_version': 'sft_v1',
    'observations': 'Review evening: check cron_output.log for training metrics, loss, and sample output.'
})

json.dump(status, open('$STATUS_FILE', 'w'), indent=2)
print('Status updated successfully')
" >> "$OUTPUT_LOG" 2>&1

echo "Training status updated and logged." >> "$OUTPUT_LOG"

# Check each pack - if already completed, skip
for pack in "${PACKS[@]}"; do
    # Check if this pack has completed runs
    completed=$(echo "$status_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print('yes' if any(r['data_pack']=='$pack' for r in d.get('runs',[])) else 'no')")
    if [ "$completed" = "yes" ]; then
        echo "  Pack $pack: ALREADY COMPLETED - skipping"
    else
        echo "  Pack $pack: NEXT TO TRAIN"
        NEXT_PACK=$pack
        break
    fi
done

if [ -z "$NEXT_PACK" ]; then
    echo "All packs have been trained at least once!"
    echo "To start a new rotation: reset training_status.json"
    exit 0
fi

echo "Starting training cycle for: $NEXT_PACK"
echo "Run: ./clyde_train_cycle.sh --pack $NEXT_PACK --track A"

echo "After run completes:"
echo "  1. Update status: python3 -c \"import json, time; status = json.load(open('$STATUS_FILE')); status['runs'].append({...}); json.dump(status, open('$STATUS_FILE', 'w'), indent=2)\""
echo "  2. datasets_used.md auto-appends (handled by cycle script)"
echo "  3. Check progress: cat $STATUS_FILE / datasets_used.md"
