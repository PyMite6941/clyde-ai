#!/bash/bash
# Clyde training cycle — runs a single pack with auto-detection and session management
set -e

CLYDE_DIR="/home/pymite6941/Clyde"
STATUS_FILE="$CLYDE_DIR/automation/training_status.json"

# ── Parse arguments first ──────────────────────────────────────────────
PACK="english"
TRACK="A"
RESUME=""
FORCE_NEW_DATA=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --pack) PACK="$2"; shift 2 ;;
        --track) TRACK="$2"; shift 2 ;;
        --resume) RESUME="$2"; shift 2 ;;
        --new-data) FORCE_NEW_DATA=true; shift 1 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

### 🛡️ SAFETY GUARDRAILS CHECK ─────────────────────────────────────────
# Prevent training on packs with inappropriate content
# These packs are pre-approved and vetted; any new packs must be reviewed

APPROVED_PACKS="english python bugs tool-use-citations fact-checking boundary-aware"

echo "🛡️ Checking safety guardrails for pack: $PACK"

# Verify pack is in approved list
if echo "$APPROVED_PACKS" | grep -qw "$PACK"; then
    echo "  ✅ Pack '$PACK' is in approved list"
else
    echo "  ⚠️ Pack '$PACK' is NOT in approved list — manual review required"
    echo "  Available packs: $APPROVED_PACKS"
    exit 1
fi

# Check sft.jsonl for prohibited patterns (strict matching, not disclaimers)
PROHIBITED_PATTERNS=(
    # Actual attack instructions (not educational security)
    "how to hack into"
    "step by step guide to break"
    "instructions for creating a"
    # Violence promotion
    "how to hurt" "how to kill" "how to harm"
    # Illegal activities
    "how to buy drugs" "how to sell drugs"
    # Weapons instructions (not hunting/self-defense educational)
    "how to make a weapon" "how to build a bomb"
)

SFT_PATH="$CLYDE_DIR/training_data/training_data/sft.jsonl"
if [ -f "$SFT_PATH" ]; then
    # Use Python for smarter matching that distinguishes disclaimers from instructions
    PROHIBITED_FOUND=$(python3 -c "
import json, re, sys
sft_path = '$SFT_PATH'
found = 0
with open(sft_path, encoding='utf-8') as f:
    for line in f:
        try:
            row = json.loads(line.strip())
            text = json.dumps(row).lower()
            # Check for actual instruction patterns (not disclaimers)
            for pattern in ['how to hack into', 'step by step guide to break', 
                    'instructions for creating a', 'how to hurt', 'how to kill', 
                    'how to harm', 'how to buy drugs', 'how to sell drugs',
                    'how to make a weapon', 'how to build a bomb']:
                # Only flag if not preceded by 'cannot', 'can\'t', 'do not', 'never'
                if re.search(pattern, text):
                    # Check for disclaimer nearby (within 50 chars)
                    ctx_start = max(0, text.find(pattern) - 50)
                    ctx = text[ctx_start:text.find(pattern) + len(pattern) + 50]
                    if not any(word in ctx for word in ['cannot', 'can\'t', 'do not', 'never', 'without', 'lack']):
                        found += 1
                        break  # count this row once
        except: continue
print(found)
" 2>/dev/null)
    if [ "$PROHIBITED_FOUND" -gt 0 ]; then
        echo "  ❌ Found $PROHIBITED_FOUND rows with prohibited content patterns in training data"
        echo "  Training data must be vetted before use"
        exit 1
    else
        echo "  ✅ No prohibited content patterns found in training data"
    fi
else
    echo "  ⚠️ Training data file not found: $SFT_PATH"
    exit 1
fi

echo "✅ Safety guardrails passed"
### ✅ END GUARDRAILS CHECK ────────────────────────────────────────────

CLYDE_DIR="/home/pymite6941/Clyde"
STATUS_FILE="$CLYDE_DIR/automation/training_status.json"

### 🛡️ SAFETY GUARDRAILS CHECK (moved after arg parsing)

CLYDE_DIR="/home/pymite6941/Clyde"
STATUS_FILE="$CLYDE_DIR/automation/training_status.json"
MD_LOG="$CLYDE_DIR/datasets_used.md"
RUNS_DIR="$CLYDE_DIR/runs"
NOTEBOOK="anthropic_student_baseline.ipynb"

# Parse arguments
PACK="english"
TRACK="A"
RESUME=""
FORCE_NEW_DATA=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --pack) PACK="$2"; shift 2 ;;
        --track) TRACK="$2"; shift 2 ;;
        --resume) RESUME="$2"; shift 2 ;;
        --new-data) FORCE_NEW_DATA=true; shift 1 ;;
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
echo "Force new data: $FORCE_NEW_DATA"
echo ""

# ==========================================
# STEP 1: Check for new data and session state
# ==========================================
echo "=== STEP 1: Session & Data Assessment ==="

# Check if there's an active session (prevent overlapping runs)
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

if [ "$ACTIVE_RUN" != "none" ] && [ -n "$ACTIVE_RUN" ]; then
    echo "⚠️  WARNING: Active run detected: $ACTIVE_RUN"
    echo "   Current session may already be training."
    echo "   Use --resume to continue, or wait for completion."
    echo ""
    read -p "Proceed anyway? (y/n) " PROCEED
    if [ "$PROCEED" != "y" ]; then
        echo "Aborting to prevent overlapping sessions."
        exit 0
    fi
fi

# Check last run results and determine if we need new data
LAST_LOSS=$(python3 -c "
import json
try:
    status = json.load(open('$STATUS_FILE'))
    runs = status.get('runs', [])
    if runs:
        last = runs[-1]
        loss = last.get('final_loss', None)
        if loss:
            print(loss)
        else:
            print('unknown')
    else:
        print('no-runs')
except: print('error')
")

echo "Last run loss: $LAST_LOSS"

# Decide if we need new data
NEED_NEW_DATA=true
if [ "$FORCE_NEW_DATA" = "true" ]; then
    echo "🔄 Force new data mode enabled"
elif [ "$LAST_LOSS" = "unknown" ] || [ "$LAST_LOSS" = "no-runs" ]; then
    echo "🆕 No previous runs — will use new data"
elif [ "$LAST_LOSS" = "error" ]; then
    echo "❌ Last run had errors — will retry with same data"
    NEED_NEW_DATA=false
elif command -v bc &>/dev/null; then
    # Check if loss is still high (above threshold)
    LOSS_THRESHOLD=0.3
    LOSS_COMPARE=$(echo "$LAST_LOSS > $LOSS_THRESHOLD" | bc -l 2>/dev/null || echo "1")
    if [ "$LOSS_COMPARE" = "1" ]; then
        echo "⚠️  Loss $LAST_LOSS above threshold $LOSS_THRESHOLD — considering new data"
        NEED_NEW_DATA=true
    else
        echo "✅ Loss $LAST_LOSS below threshold $LOSS_THRESHOLD — data seems sufficient"
        NEED_NEW_DATA=false
    fi
else
    echo "⚠️  bc not available — assuming need for new data"
    NEED_NEW_DATA=true
fi

if [ "$NEED_NEW_DATA" = "true" ]; then
    echo "🔍 Checking for new/updated data packs..."
    # Check if the data pack has been used recently
    DATA_PACKS=("english" "python" "bugs" "mixed" "tool-use-citations" "fact-checking" "boundary-aware")
    PACK_INDEX=-1
    for i in "${!DATA_PACKS[@]}"; do
        if [ "${DATA_PACKS[$i]}" = "$PACK" ]; then
            PACK_INDEX=$i
            break
        fi
    done

    if [ $PACK_INDEX -ge 0 ]; then
        # Check rotation - if this pack was recently used, consider next one
        RECENT_RUNS=$(python3 -c "
import json, re
try:
    md = open('$MD_LOG').read()
    # Find recent entries for this pack
    pattern = '\\| ' + '$PACK' + ' \\|'
    matches = re.findall(pattern, md)
    print(len(matches))
except: print('0')
")
        echo "Recent runs for $PACK: $RECENT_RUNS"

        if [ "$RECENT_RUNS" -gt 0 ] && [ "$RECENT_RUNS" -lt 3 ]; then
            echo "🔄 Less than 3 runs on $PACK — proceeding with current data"
        elif [ "$RECENT_RUNS" -ge 3 ]; then
            echo "🔄 3+ runs on $PACK — consider rotating to next pack"
            # Auto-rotate to next pack
            NEXT_INDEX=$(( (PACK_INDEX + 1) % ${#DATA_PACKS[@]} ))
            PACK="${DATA_PACKS[$NEXT_INDEX]}"
            RUN_NAME="${TRACK}-${PACK}-${DATE_SUFFIX}"
            echo "🔄 Auto-rotated to pack: $PACK"
        fi
    fi
fi

echo "Using pack: $PACK"
echo ""

# ==========================================
# STEP 2: Update notebook control cell
# ==========================================
echo "=== STEP 2: Notebook Control Cell Update ==="

# Update Cell 1 in the notebook with the current run settings
python3 -c "
import json
nb_path = '$CLYDE_DIR/$NOTEBOOK'
with open(nb_path) as f:
    nb = json.load(f)

# Cell 1 is the control cell (index 1)
cell1 = nb['cells'][1]
source = cell1['source']

# Convert to mutable list if needed
if isinstance(source, list):
    pass  # already mutable
else:
    source = [line + '\n' for line in source]
    cell1['source'] = source

# Find and update the control variables
new_lines = []
i = 0
while i < len(source):
    line = source[i]
    if line.startswith('MODE = '):
        new_lines.append(f'MODE = \"train\"           # \"smoke\" = short Kaggle test | \"train\" = real session')
    elif line.startswith('TRACK = '):
        new_lines.append(f'TRACK = \"{TRACK}\"  # from-scratch tiny GPT')
    elif line.startswith('DATA_PACK = '):
        new_lines.append(f'DATA_PACK = \"{PACK}\"    # \"english\" | \"python\" | \"bugs\" | \"mixed\"')
    elif line.startswith('RUN_NAME = '):
        new_lines.append(f'RUN_NAME = \"{RUN_NAME}\"   # new folder every run')
    elif line.startswith('RESUME_FROM = '):
        new_lines.append(f'RESUME_FROM = {RESUME_FROM_ARG}       # e.g. \"runs/A-english\" ; None = start fresh')
    elif line.startswith('HYPOTHESIS = '):
        # Keep existing or set default
        if i + 1 < len(source) and 'HYPOTHESIS' in source[i+1]:
            new_lines.append(line)
        else:
            new_lines.append(f'HYPOTHESIS = \"Track {TRACK} on {PACK} will train factual assistant with proper citations.\"')
    elif line.startswith('SUCCESS_IF = '):
        if i + 1 < len(source) and 'SUCCESS_IF' in source[i+1]:
            new_lines.append(line)
        else:
            new_lines.append(f'SUCCESS_IF = \"loss falls across printed steps AND sample contains coherent {PACK} content.\"')
    elif line.startswith('TRACK_A_STEPS = ') or line.startswith('TRACK_B_MAX_STEPS = '):
        # Keep existing steps
        new_lines.append(line)
    else:
        new_lines.append(line)
    i += 1

cell1['source'] = new_lines

with open(nb_path, 'w') as f:
    json.dump(nb, f, indent=1)
print('✅ Notebook Cell 1 updated')
"

echo "✅ Notebook control cell updated"
echo ""

# ==========================================
# STEP 3: Run the notebook training
# ==========================================
echo "=== STEP 3: Training Execution ==="
echo "📝 Next: Run the Kaggle notebook manually"
echo "   - Open anthropic_student_baseline.ipynb in Kaggle"
echo "   - Ensure dataset 'clyde-training-data' is attached"
echo "   - Cell 1 is already configured"
echo "   - Run all cells (0 through 11)"
echo "   - Save Version with output included"
echo ""
echo "⏳ Training will run 300 steps on pack: $PACK"
echo ""

# ==========================================
# STEP 4: Post-training assessment and recording
# ==========================================
echo "=== STEP 4: Post-Training Assessment ==="

# Wait for user to complete the run
read -p "Press Enter after you've completed the Kaggle notebook run and saved Version: " -t 300

if [ $? -eq 124 ]; then
    echo "⏰ Timeout — proceeding with available data"
fi

# Update training status from the completed run
echo "Updating training status..."

python3 << 'PYEOF'
import json
import os

status_file = os.path.expanduser("~/Clyde/automation/training_status.json")
clyde_dir = os.path.expanduser("~/Clyde")

# Read current status
try:
    with open(status_file) as f:
        status = json.load(f)
except:
    status = {"version": "1.0", "created": __import__("datetime").datetime.now().isoformat(), "runs": [], "current_run": None}

# Check if there's a recent run directory
runs_dir = os.path.join(clyde_dir, "runs")
if os.path.exists(runs_dir):
    run_dirs = [d for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d))]
    if run_dirs:
        # Get the most recent run
        latest_run = sorted(run_dirs)[-1]
        latest_path = os.path.join(runs_dir, latest_run)
        
        # Check for meta.json
        meta_path = os.path.join(latest_path, "meta.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            
            # Check if this run is already tracked
            run_names = [r.get("run_name") for r in status.get("runs", [])]
            if meta.get("run_name") not in run_names:
                # Add new run entry
                new_run = {
                    "run_name": meta.get("run_name"),
                    "data_pack": meta.get("data_pack"),
                    "track": meta.get("track"),
                    "steps_this_run": meta.get("steps_this_run"),
                    "final_loss": meta.get("final_loss"),
                    "date_started": meta.get("date_started", ""),
                    "date_completed": __import__("datetime").datetime.now().isoformat(),
                    "observations": meta.get("observations", "Training completed on " + meta.get("data_pack", "unknown") + " pack")
                }
                status.setdefault("runs", []).append(new_run)
                # Keep only last 50 runs to avoid bloat
                if len(status["runs"]) > 50:
                    status["runs"] = status["runs"][-50:]
                
                # Update last_run
                status["last_run"] = meta.get("run_name")
                
                # Write updated status
                with open(status_file, 'w') as f:
                    json.dump(status, f, indent=2)
                
                print(f"✅ Added run {meta.get('run_name')} to training status")
                print(f"   Pack: {meta.get('data_pack')}, Loss: {meta.get('final_loss')}")
            else:
                print("ℹ️  Run already tracked in status")
        else:
            print("⚠️  No meta.json found in latest run directory")
    else:
        print("⚠️  No run directories found")
else:
    print("⚠️  Runs directory not found")

PYEOF

# ==========================================
# STEP 5: Update datasets_used.md
# ==========================================
echo "=== STEP 5: Dataset Log Update ==="

python3 << 'PYEOF'
import json
import os
import re

clyde_dir = os.path.expanduser("~/Clyde")
status_file = os.path.join(clyde_dir, "automation", "training_status.json")
md_file = os.path.join(clyde_dir, "datasets_used.md")

# Read current status
try:
    with open(status_file) as f:
        status = json.load(f)
except:
    status = {"runs": []}

# Read current markdown
try:
    with open(md_file) as f:
        md_content = f.read()
except:
    md_content = """# Clyde Training Datasets Log

This file tracks all datasets used for Clyde training and testing.

## Dataset Overview

| Dataset | Packs | Runs | Status | Date Started | Date Completed | Loss | Observations |
|---------|-------|------|--------|-------------|---------------|------|-------------|
"""
# Check if we need headers

# Get recent runs
runs = status.get("runs", [-1:])  # Get last run or empty

for run in runs[-1:]:  # Just the most recent
    run_name = run.get("run_name", "unknown")
    data_pack = run.get("data_pack", "unknown")
    track = run.get("track", "unknown")
    steps = run.get("steps_this_run", "?")
    loss = run.get("final_loss", "?")
    date_started = run.get("date_started", "")
    date_completed = run.get("date_completed", "")
    observations = run.get("observations", "No observations recorded")
    
    # Parse date formats
    if date_started:
        try:
            from datetime import datetime
            ds = datetime.strptime(date_started, "%Y-%m-%dT%H:%M:%S")
            date_started_formatted = ds.strftime("%Y-%m-%d")
        except:
            date_started_formatted = date_started[:10] if len(date_started) > 10 else date_started
    else:
        date_started_formatted = "?"
    
    if date_completed:
        try:
            from datetime import datetime
            dc = datetime.strptime(date_completed, "%Y-%m-%dT%H:%M:%S")
            date_completed_formatted = dc.strftime("%Y-%m-%d")
        except:
            date_completed_formatted = date_completed[:10] if len(date_completed) > 10 else date_completed
    else:
        date_completed_formatted = "?"
    
    # Add to markdown table
    new_row = f"| {run_name} | {data_pack} | {steps} | completed | {date_started_formatted} | {date_completed_formatted} | {loss} | {observations} |\n"
    
    # Check if this entry already exists
    pattern = rf"\\| {re.escape(run_name)} \\|"
    if not re.search(pattern, md_content):
        # Add after header
        if "| Dataset |" in md_content:
            # Insert after header row
            lines = md_content.split("\n")
            insert_idx = None
            for i, line in enumerate(lines):
                if line.startswith("| Dataset |"):
                    insert_idx = i + 2  # After the header and separator
                    break
            if insert_idx and insert_idx < len(lines):
                lines.insert(insert_idx, new_row)
                md_content = "\n".join(lines)
        else:
            md_content += "\n" + new_row

with open(md_file, 'w') as f:
    f.write(md_content)
print(f"✅ Updated datasets_used.md with {run_name}")
PYEOF

echo "✅ Dataset log updated"
echo ""

# ==========================================
# STEP 6: Session termination check
# ==========================================
echo "=== STEP 6: Session Management ==="

# Check if we should end the session
python3 << 'PYEOF'
import json
import os

status_file = os.path.expanduser("~/Clyde/automation/training_status.json")
runs_file = os.path.join(os.path.expanduser("~/Clyde"), "automation", "run_log.txt")

# Read status
try:
    with open(status_file) as f:
        status = json.load(f)
except:
    status = {}

# Check completed runs
runs = status.get("runs", [])
completed_runs = [r for r in runs if r.get("final_loss") is not None]

if completed_runs:
    last_loss = completed_runs[-1].get("final_loss", 0)
    print(f"📊 Last run loss: {last_loss}")
    
    # If loss is very low (model converged), suggest session end
    if last_loss < 0.1:
        print("✅ Model appears to have converged (loss < 0.1)")
        print("💡 Consider: session training complete, can standby")
    elif last_loss > 0.5:
        print("⚠️  Model loss still high ( > 0.5 ) — may need more data or different pack")
    
    # Record in run log
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_name = completed_runs[-1].get("run_name", "unknown")
    pack = completed_runs[-1].get("data_pack", "unknown")
    
    log_entry = f"# {now} - Run {run_name} on pack {pack} - Loss: {last_loss} - Status: completed\n"
    
    # Append to run log
    with open(runs_file, 'a') as f:
        f.write(log_entry)
    print(f"📝 Added entry to run_log.txt")
    
except Exception as e:
    print(f"⚠️  Error in session assessment: {e}")
PYEOF

echo ""
echo "=== CLYDE TRAINING CYCLE COMPLETE ==="
echo "Run: $RUN_NAME"
echo "Pack: $PACK"
echo "Track: $TRACK"
echo ""
echo "Next steps:"
echo "1. Check: cat $STATUS_FILE"
echo "2. Check: cat $MD_LOG"
echo "3. Next cron run (12h): will rotate to next pack automatically"
echo ""
