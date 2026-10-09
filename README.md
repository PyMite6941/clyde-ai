# Clyde AI Training & Interface Framework

## Overview

Clyde is a local AI training and orchestration framework running on Raspberry Pi, coordinated by Hermes Agent with Paperclip agent workflows. The system manages training cycles, interface design, and tool integration for local AI workloads.

## Architecture

### Model Strategy: **4 Specialized Models with Your Names** (Your Setup)

Clyde uses 4 specialized models, each trained on domain-specific data with the names you chose:

| Model Name | Focus | Training Data | Purpose |
|------------|-------|---------------|---------|
| **Picasso** | Art/Design | boundary-aware + fact-checking packs (10 examples) | Creative tasks, design, visual arts |
| **Euler** | Math/Physics | reasoning pack (10 examples) | Mathematical reasoning, physics problems |
| **Bellard** | Computing/Programming | tool-use-citations + python + bugs (23 examples) | CLI commands, programming, system administration |
| **Others** | General/Chat | english + mixed packs (8 examples) | Everyday questions, general chat |

### Key Advantages

- **Your named models** — Picasso for art, Euler for math, Bellard for computing, plus Others for general
- **Rate limiting distributed** across providers (OpenRouter, Groq, NVIDIA)
- **Cost optimized** per task type (use fastest/cheapest model for each domain)
- **Better performance** per domain vs. one "jack-of-all-trades" model
- **Resilience** — if one provider has issues, others continue working
- **Matches Paperclip orchestration** pattern you already use

### Git Protection

Training data and cron logs are gitignored to prevent PII/secret leaking:

```gitignore
# Training data - contains PII and sensitive content, NOT for repo
training_data/**

# Cron logs - runtime outputs, not tracked
cron_logs/**

# Automation runtime logs
/automation/cron_output.log
/automation/training_status.json
/automation/run_log.txt
```

## Commit History

Recent commits add interfaces, training foundation with your model names, and proper gitignore protection for sensitive data.

## Setup

- **Host:** Raspberry Pi (Linux 6.18.50+rpt-rpi-v8)
- **User:** pymite6941 — AI enthusiast, free-tier LLM APIs (OpenRouter, Groq, NVIDIA)
- **Coordination:** Hermes Agent + Paperclip orchestration
- **Cron:** 8 pack rotation schedules + daily evaluation
- **Model data:** 4 specialized JSONL files in `training_data/models/`

## Quick Start

```bash
# View crontab
crontab -l

# Check gitignored directories
git check-ignore training_data/
git check-ignore cron_logs/

# Model data locations
ls training_data/models/
```