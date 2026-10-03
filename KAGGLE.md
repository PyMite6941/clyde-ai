# Clyde / student baseline — preferred Kaggle setup

Use **Kaggle** as the training machine. Use the Windows laptop only to edit data and read samples. Use the Pi only after you have a saved adapter or GGUF.

This matches the files already in this folder:

- `anthropic_student_baseline.ipynb` — the one notebook
- `training_data/sft.jsonl` — train rows
- `training_data/eval.jsonl` — never train on this
- `tiny_gpt_walkthrough.py` / `hf_code_rewriter.py` — local explainers, not the Kaggle job
- `lab_log.md` — one experiment per block; fill this or you are only pressing Run all

---

## The framework (what you are actually developing)

```
data you wrote          training_data/sft.jsonl
        │
        ▼
recipe notebook         TRACK A = your tiny GPT
                        TRACK B = LoRA on Qwen 0.5B
        │
        ▼
Kaggle T4 job           runs/<RUN_NAME>/  + printed SAMPLE
        │
        ▼
your judgment           lab_log.md + eval.jsonl
        │
        ▼
next hypothesis         change ONE thing, run again
```

You are not building Claude. You are running a **lab**:

| Layer | What it is | You own this by… |
|---|---|---|
| Base model (Track B) | Qwen weights someone else pretrained | crediting Qwen, not claiming you trained them |
| Architecture (Track A) | tiny GPT in the notebook | explaining embeddings, attention, loss |
| Recipe | SFT / LoRA / resume | changing `MODE`, steps, pack |
| Data | jsonl + packs | writing rows you can defend |
| Eval | `eval.jsonl` + samples | scoring by hand before the next run |
| Product later | Pi + GGUF | only after Track B eval is less embarrassing |

Planning rule: **one variable per run**. Pack *or* steps *or* resume source — not all three plus a new model.

---

## Session 0 — wiring test (do this first)

Goal: prove Kaggle GPU + the notebook save a run. Not “Clyde is smart.”

1. Kaggle → Code → New notebook → File → Import `anthropic_student_baseline.ipynb`.
2. Rename to `clyde-smoke`.
3. Settings → Accelerator **GPU T4**, Internet **On**, notebook **Private**.
4. Leave the control cell as shipped:
   - `MODE = "smoke"`
   - `TRACK = "A"`
   - `DATA_PACK = "english"`
   - `RUN_NAME = "A-smoke-1"`
   - `RESUME_FROM = None`
5. Run all.
6. Pass if **all** of these are true:
   - first prints include `cuda: True` and a GPU name
   - `PLAN` block prints your hypothesis
   - loss at the last step is **lower** than step 1
   - a `=== SAMPLE ===` block prints
   - `runs/A-smoke-1/model.pt` exists under Output after **Save Version**
7. Copy the PLAN + last loss + 3 lines of sample into `lab_log.md`.

If `cuda: False`, stop. Verify phone + GPU setting, restart session, do not start Track B.

Smoke Track B (`MODE="smoke"`, `TRACK="B"`) is a **second** session: it downloads ~1 GB and should only run after Session 0 passed.

---

## Why Kaggle for this project

| Need | Kaggle setting I want |
|---|---|
| Weekly GPU time you can plan around | ~30 hours/week (resets on Kaggle’s schedule) |
| Session length | Stay under ~9–11 hours per session |
| Files that survive a crash | **Save Version** after every good run |
| Downloads (Qwen, pip) | Settings → Internet **ON** |
| GPU | Settings → Accelerator → **GPU T4** (or T4x2 if T4 is busy) |
| Tracking | No W&B account. The notebook already sets `WANDB_DISABLED=true` |

Do not use Kaggle TPU for this notebook. Do not start Track B on CPU.

Phone verification is often required before GPUs turn on. Do that in Kaggle account settings first or the accelerator silently falls back to CPU.

---

## One-time account + notebook import

1. Log in at [kaggle.com](https://www.kaggle.com).
2. Code → **New notebook**.
3. File → **Import notebook** → upload `anthropic_student_baseline.ipynb`.
4. Rename the notebook to `clyde-track-a` or `clyde-track-b` so versions stay obvious.
5. Right sidebar **Settings**:
   - Persistence → **Files only** if you see it (keeps `/kaggle/working` a bit longer).
   - Accelerator → **GPU T4**.
   - Internet → **On**.
   - Privacy → Private while you learn.
6. Confirm GPU in the first code output. You must see `cuda: True` and a GPU name. If you see CPU only, stop and fix Settings. Track B will crawl and look like it “trained.”

---

## One-time data upload (do this before Track B with your own rows)

Kaggle notebooks do not keep random leftover files unless they are a **Dataset** or a **saved version output**.

Preferred layout:

1. On the laptop, keep:
   - `training_data/sft.jsonl`
   - `training_data/eval.jsonl`
2. Kaggle → Datasets → **New dataset** → upload that folder.
3. Name it `clyde-training-data`.
4. In the notebook: Add data → attach `clyde-training-data`.

It mounts at something like:

```text
/kaggle/input/clyde-training-data/sft.jsonl
/kaggle/input/clyde-training-data/eval.jsonl
```

The first version of the notebook trains from packs **baked into cells**. That is fine for run 1. When you add your own bugs, attach the dataset and point Track B at the jsonl (boilerplate below).

Never attach `eval.jsonl` as training input.

---

## Preferred run order

Do not jump to Track B on day one.

| # | TRACK | DATA_PACK | RUN_NAME | RESUME_FROM | Why |
|---|---|---|---|---|---|
| 1 | `A` | `english` | `A-english` | `None` | Prove GPU + save/load |
| 2 | `A` | `python` | `A-python` | `runs/A-english` | Prove resume |
| 3 | `B` | `mixed` | `B-mixed` | `None` | First real assistant |
| 4 | `B` | `bugs` | `B-bugs` | `runs/B-mixed` | Specialize without starting over |
| 5 | — | — | — | — | Score `eval.jsonl` by hand. Do not train. |

Edit **only** the control cell, then Run all.

```python
# =========================
# EDIT THIS CELL EACH RUN
# =========================
TRACK = "A"
DATA_PACK = "english"
RUN_NAME = "A-english"
RESUME_FROM = None

TRACK_A_STEPS = 300
TRACK_B_MAX_STEPS = 60
SEED = 42
```

After run 1 finishes:

```python
TRACK = "A"
DATA_PACK = "python"
RUN_NAME = "A-python"
RESUME_FROM = "runs/A-english"
```

After the first Track B:

```python
TRACK = "B"
DATA_PACK = "bugs"
RUN_NAME = "B-bugs"
RESUME_FROM = "runs/B-mixed"
```

Rules:

- New `RUN_NAME` every run or you overwrite the last folder.
- `RESUME_FROM` is a **folder path**, not a `.pt` file.
- Track A resume needs `runs/<name>/model.pt`.
- Track B resume needs `runs/<name>/adapter_config.json`.
- If you change `n_embd` / `n_layer` in the notebook, you cannot resume Track A. Start a new family (`A2-english`, …).

---

## What “done” looks like for one session

Printed at the bottom:

```text
step 300  loss=...
=== SAMPLE after A-english on pack english ===
...
=== end sample ===
Next run: set RESUME_FROM = runs/A-english
```

Then immediately:

1. **Save Version** → Quick save → “always save output.”
2. Open that version’s **Output** and check `runs/<RUN_NAME>/` is there.
3. Download `runs/` to the laptop if you care about that checkpoint.

If you skip Save Version, Kaggle can wipe `/kaggle/working` when the session dies. That is the usual way people “lose Clyde.”

---

## Boilerplate I want in Kaggle (copy if you extend the notebook)

### 0. Environment guard (top of a new cell, before training)

```python
import os, sys, torch
os.environ["WANDB_DISABLED"] = "true"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

assert os.path.isdir("/kaggle"), "This cell is for Kaggle"
print("working:", os.getcwd())          # should be /kaggle/working
print("cuda:", torch.cuda.is_available())
if torch.cuda.is_available():
    print(torch.cuda.get_device_name(0))
else:
    raise SystemExit("No GPU. Settings → Accelerator → GPU T4, then restart session.")
```

### 1. Where files should live

```python
from pathlib import Path

WORKING = Path("/kaggle/working")
RUNS = WORKING / "runs"
RUNS.mkdir(exist_ok=True)

INPUT = Path("/kaggle/input")
# After you attach the dataset, pick the actual folder name:
# list(INPUT.iterdir())
DATA = INPUT / "clyde-training-data"    # change if your dataset slug differs
print("runs ->", RUNS)
print("data ->", DATA, "exists:", DATA.exists())
```

Kaggle **input** is read-only. Write checkpoints only under `/kaggle/working/runs/`.

### 2. Load *your* jsonl for Track B (optional; after dataset is attached)

```python
import json
from pathlib import Path

def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

sft_path = Path("/kaggle/input/clyde-training-data/sft.jsonl")
eval_path = Path("/kaggle/input/clyde-training-data/eval.jsonl")

if sft_path.exists():
    all_rows = load_jsonl(sft_path)
    # Keep packs separate so DATA_PACK still means something
    SFT_PACKS = {"english": [], "python": [], "bugs": [], "mixed": []}
    for row in all_rows:
        pack = row.get("pack", "mixed")
        item = {"user": row["user"], "assistant": row["assistant"]}
        SFT_PACKS.setdefault(pack, []).append(item)
        SFT_PACKS["mixed"].append(item)
    print({k: len(v) for k, v in SFT_PACKS.items()})
else:
    print("no dataset attached; using packs inside the notebook")
```

Do **not** load `eval.jsonl` into `SFT_PACKS`.

### 3. Hand-score eval after Track B (no training)

```python
# Use the model already in memory at the end of Track B,
# or load SAVE_DIR from the last run.
eval_rows = load_jsonl(Path("/kaggle/input/clyde-training-data/eval.jsonl"))
for i, row in enumerate(eval_rows, 1):
    print("=" * 60)
    print("EVAL", i, row.get("pack"))
    print(row["user"][:500])
    print("hint:", row.get("note", ""))
```

Paste each `user` into the same generate call Track B uses. Judge by hand against `good_fix_must_include`. Write failures as **new** rows in `sft.jsonl` on the laptop, re-upload the dataset, train again.

### 4. Persist a run so the next session can resume

Kaggle cannot see last week’s `/kaggle/working` unless you saved it.

Options I prefer, in order:

1. **Save Version** with output, then in a *new* session:  
   File → add data → **Notebook output files** → pick that version.  
   Copy into working:

```python
from pathlib import Path
import shutil

# Change the slug to your saved-output path shown in the Add data panel
src = Path("/kaggle/input/clyde-track-a/runs/A-english")
dst = Path("/kaggle/working/runs/A-english")
if src.exists() and not dst.exists():
    shutil.copytree(src, dst)
print("resume candidates:", list(Path("/kaggle/working/runs").glob("*")))
```

2. Download `runs/` to the laptop after every good run. Re-upload as a dataset named `clyde-checkpoints` if Save Version is messy.

Set `RESUME_FROM = "runs/A-english"` only after that folder exists **in this session**.

---

## Track A vs Track B on Kaggle quotas

| Track | Internet | Time on T4 | Quota habit |
|---|---|---|---|
| A | Off is OK after first pip-less run | a few minutes | Use this to test resume logic |
| B first run | **On** (downloads Qwen ~1 GB + pip) | 10–25 min + download | One B run per sitting until you know it saves |
| B later runs | On still safest (HF may fetch tokenizer files) | similar | Resume adapter, do not download a new base if cached |

If pip or `from_pretrained` hangs, Internet is off or the session is out of quota.

Stay on `Qwen/Qwen2.5-0.5B-Instruct` until eval scores move. A 7B model is the wrong fight for a Pi and a free T4.

---

## What I do not want you to do on Kaggle

- Run Track B with no GPU and assume 2 hours of CPU is “training.”
- Train on `eval.jsonl`.
- Reuse the same `RUN_NAME` and then wonder where run 1 went.
- Leave the tab idle until Kaggle kills the session mid-save.
- Turn on W&B and leak the run to a public project.
- Import this notebook into a **public** notebook that reprints your private homework code.
- Start PPO / full-parameter fine-tunes. This project is LoRA SFT + later DPO.

---

## Honest label for Clyde (put in the notebook title cell if you share a version)

```text
Clyde is a LoRA fine-tune of Qwen2.5-0.5B-Instruct.
Base weights: Alibaba Qwen (Apache 2.0), not trained here.
Data: training_data/sft.jsonl written by me.
Trainer: Hugging Face Transformers + PEFT, run on Kaggle T4.
```

---

## Session checklist

- [ ] GPU T4 + Internet on  
- [ ] First print shows `cuda: True`  
- [ ] Control cell has a **new** `RUN_NAME`  
- [ ] `RESUME_FROM` exists in `/kaggle/working` or is `None`  
- [ ] Eval file is not in the train list  
- [ ] Sample printed and read  
- [ ] Save Version with output  
- [ ] `runs/<RUN_NAME>/meta.json` downloaded or visible in Output  

Laptop next: add 10 real bugs to `sft.jsonl`, re-upload the dataset, Track B `DATA_PACK="bugs"`, resume from last `B-...` folder.
