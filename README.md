# Clyde AI Training & Interface Framework

## Overview

Clyde is a local AI training and orchestration framework running on Raspberry Pi, coordinated by Hermes Agent with Paperclip agent workflows. The system manages training cycles, interface design, and tool integration for local AI workloads.

## Architecture

### Model Fleet: **4 Specialized Models with Your Names** (Your Design)

Clyde uses 4 specialized models, each trained on domain-specific data with the names you chose:

| Model Name | Focus | Training Data | Specialization |
|------------|-------|---------------|----------------|
| **Picasso** | Art/Design | boundary-aware + fact-checking packs (10 examples) | Creative tasks, design, visual arts, aesthetic judgment |
| **Euler** | Math/Physics | reasoning pack (10 examples) | Mathematical reasoning, physics problems, logical inference |
| **Bellard** | Computing/Programming | tool-use-citations + python + bugs (23 examples) | CLI commands, programming, system administration, debugging |
| **Others** | General/Chat | english + mixed packs (8 examples) | Everyday questions, general conversation, creative writing |

### Model Fleet Design

Each model is trained on carefully split data to develop domain expertise:

- **Picasso** (10 examples) — Art and design reasoning, trained on boundary-aware and fact-checking domain knowledge
- **Euler** (10 examples) — Mathematical and physical reasoning, trained on logical inference and puzzle-solving patterns
- **Bellard** (23 examples) — Computing and computer science, trained on tool usage, programming questions, and system administration tasks
- **Others** (8 examples) — General conversational ability, trained on English rewriting and mixed-topic questions

### Key Fleet Characteristics

- **Four named models** — Picasso, Euler, Bellard, Others — each with a distinct domain focus
- **Domain-specialized** — each model develops expertise in its assigned area through targeted training data
- **Complementary coverage** — together they cover art/design, math/physics, computing, and general conversation
- **Training data is gitignored** — `training_data/` contains your model training sets and stays local

### Model Data Location

Training data for each model is stored in `training_data/models/`:

```
training_data/models/
├── picasso.jsonl     — 10 art/design examples
├── euler.jsonl       — 10 math/physics examples
├── bellard.jsonl     — 23 computing/programming examples
└── others.jsonl      — 8 general chat examples
```

All training data is gitignored to keep sensitive content and PII off GitHub.

## Quick Start

```bash
# View model training data
ls training_data/models/

# Check gitignored directories
git check-ignore training_data/
```

## Commit History

Recent commits add your 4-model fleet design, interface documentation, and gitignore protections.

## Setup

- **Host:** Raspberry Pi (Linux 6.18.50+rpt-rpi-v8)
- **User:** pymite6941 — AI enthusiast designing specialized model fleet
- **Coordination:** Hermes Agent + Paperclip orchestration
- **Model data:** 4 specialized JSONL files in `training_data/models/`
- **Cron:** 8 pack rotation schedules + daily evaluation

## Related

- `clyde-training-workflow` — Complete training cycle management
- `clyde-tools` — Tool ecosystem (video, graphics, browser, presentations)
- `hermes-agent` — Central coordination skill