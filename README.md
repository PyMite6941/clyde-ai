# Clyde AI Training & Interface Framework

## Overview

Clyde is a local AI training and orchestration framework running on Raspberry Pi, coordinated by Hermes Agent with Paperclip agent workflows. The system manages training cycles, interface design, and tool integration for local AI workloads.

## Architecture

### Model Strategy: **3-5 Specialized Models** (Recommended)

Given free-tier API constraints and rate limiting concerns, Clyde uses specialized models rather than one monolithic model:

| Domain | Recommended Provider | Model |
|--------|---------------------|-------|
| **Coding** | Groq | Fast inference for development tasks |
| **Math/Reasoning** | NVIDIA | nemotron-3.5-lightning-30b-a3b (primary) |
| **Design/Creative** | OpenRouter | mixtral / claude variants for interface design |
| **Analysis/Research** | NVIDIA | Larger models for training data analysis |
| **Fallback** | Any free tier | Cost-effective for non-critical tasks |

### Key Advantages

- **Rate limiting distributed** across providers (OpenRouter, Groq, NVIDIA)
- **Cost optimized** per task type (use fastest/cheapest for each use case)
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

Recent commits add interfaces, training foundation, and proper gitignore protection for sensitive data.

## Setup

- **Host:** Raspberry Pi (Linux 6.18.50+rpt-rpi-v8)
- **User:** pymite6941 — AI enthusiast, free-tier LLM APIs (OpenRouter, Groq, NVIDIA)
- **Coordination:** Hermes Agent + Paperclip orchestration
- **Cron:** 8 pack rotation schedules + daily evaluation

## Quick Start

```bash
# View crontab
crontab -l

# Check gitignored directories
git check-ignore training_data/
git check-ignore cron_logs/
```

## Related Skills

- `clyde-training-workflow` — Complete training cycle management
- `clyde-tools` — Tool ecosystem (video, graphics, browser, presentations)
- `hermes-agent` — Central coordination skill