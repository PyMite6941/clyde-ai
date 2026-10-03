# Clyde Research — Tool-Use + Source Citation Training (2026)

## Core Principle: Quality Over Quantity
- 500 well-curated tool-use examples beat 50k noisy ones (LIMA result still holds)
- TL-Training paper: 1,217 carefully constructed data points matches or exceeds larger models
- Error categories (from analysis): tool selection → parameter identification → content generation

## Training Data Structure
Each example follows this format:
```json
{
  "pack": "tool-use-citations",
  "user": "Natural language question about tool usage", 
  "assistant": "Direct answer + command + explanation",
  "source_citation": "Verifiable source(s) for the information"
}
```

## Key Insights from Research Papers

### 1. TL-Training (arxiv/2412.15495)
- **Finding**: Token importance is distributed unevenly in tool-use training
- **Method**: MAE (token Masking) and PKT (token-level weighting) strategies
- **Result**: 1,217 data points with weighting matches larger models trained on 100k+
- **Error categories observed**:
  - Tool selection errors (choosing wrong tool with similar name)
  - Parameter identification errors (wrong flags/arguments)
  - Content generation errors (incorrect output processing)
- **Recommendation**: Dynamically adjust token weights to prioritize key tokens

### 2. ToolBench (arxiv/2307.16789)
- **Dataset**: 16,464 real-world REST APIs from RapidAPI Hub (49 categories)
- **Construction**: Automatic via ChatGPT with function call capabilities
- **Structure**: (instruction, relevant API(s), solution path annotation)
- **Key addition**: API documentation embedding (helps generalization to new APIs)
- **Training**: LLaMA-2 7B fine-tuned for 2 epochs, lr=5e-5, batch=64
- **Evaluation**: Single-tool, intra-category multi-tool, inter-category multi-tool
- **Generalization levels**: Inst. (unseen instructions), Tool (unseen tools same category), Cat. (unseen categories)

### 3. ToolQA (arxiv/2306.13304)
- **Purpose**: Benchmark for QA with external tools
- **8 domains**: temporal (Flights, Coffee), spatial (Yelp, Airbnb), mathematical (GSM8K), scientific (SciREX), personal (synthesized agenda), social (DBLP graphs)
- **13 tool types**: text retrieval, database ops, code interpretation, math computations, etc.
- **Three-phase generation**: Reference data collection → human-guided question gen → programmatic answer gen
- **Critical**: Reference corpora must NOT overlap with LLM pre-training data

### 4. LIMA Paper (Core Finding)
- **500 well-curated examples** can outperform 50k noisy examples
- **Instruction tuning** format: `{"instruction": "...", "response": "..."}` or chat format
- **Key**: Deduplication, quality filtering, length balancing are more important than scale
- **Synthetic data warning**: Never train on synthetic data from same model (model collapse)

## Clyde-Specific Training Recommendations

### Phase 1: SFT on Tool-Use + Citations (Current Setup)
**Data**: Your 15 pairs + existing 12 pairs = 27 total
- Focus: Correct command format + source citation habit
- Pack: `tool-use-citations`
- VRAM: ~2-4GB (Tiny GPT, N_embd=128, n_layer=2)
- Steps: 300 (smoke) or 1000 (train)

**Prompt pattern** (Cell 0 system prompt + user query):
```
Q: "How do I check CPU temp on Raspberry Pi?"
A: "Use `vcgencmd measure_temp`. This prints the CPU temperature in Celsius. Source: Raspberry Pi foundation documentation and vcgencmd utility."
```

### Phase 2: Expand Data (Recommended Next Step)
**Sources for more quality data**:
1. **ToolBench-lite**: Subset of 100 APIs most relevant to Pi/Linux tasks
2. **Personal command logs**: Your own terminal history (anonymized)
3. **FAQ-style Q&A**: Common Pi/admin questions with verified answers
4. **Error-pattern data**: Specifically pairing "wrong command" → "correct command"

**Target**: 100-200 pairs total (still well within LIMA-range of effectiveness)

### Phase 3: DPO for "Not Yes-Man" on Tool Use
**Data format**: (prompt, chosen, rejected)
- **Chosen**: Correct command with source citation
- **Rejected**: Common mistake (e.g., `cat /etc/passwd` when user meant `ls`, or hallucinated command)
- **Source**: Could generate rejections from the SFT model itself, then hand-curate

**Example**:
```json
{
  "prompt": "How do I list files in a directory?",
  "chosen": "Use `ls`. Source: POSIX specification, standard Linux utility.",
  "rejected": "Use `dir`. (Common mistake: `dir` is not standard on Linux, use `ls` instead.)"
}
```

### Phase 4: RAG Integration (Future)
When Clyde encounters a tool/use question outside his training data:
1. Check if similar command in his SFT data (pattern match)
2. If not: "I couldn't verify this command from my training data. For Raspberry Pi, try `man <command>` or https://www.raspberrypi.com/documentation/"
3. Never hallucinate a command — always cite knowledge boundaries

## Storage Structure (Clyde/)
```
Clyde/
├── research/
│   ├── training_best_practices.md          ← just saved
│   └── tool_use_training.md                ← will save below
├── training_data/
│   ├── sft.jsonl                           ← 27 Q&A pairs (12 original + 15 new)
│   ├── eval.jsonl                          ← hand-evaluated facts
│   └── packs/
│       ├── english/                        ← original packs
│       ├── tool-use/                       ← original tool-use
│       └── tool-use-citations/             ← new: citations focus
├── runs/
├── lab_log.md
├── config.yaml
└── KAGGLE.md
```

## Quick Checklist Before Each Training Run
- [ ] Data deduplicated (no exact duplicate user queries)
- [ ] Eval set held out (never seen by model during training)
- [ ] Source citations present in every answer (form: "Source: ...")
- [ ] Chat template verified (print 5 training examples from sft.jsonl)
- [ ] Learning rate set (2e-4 for SFT from scratch)
- [ ] Steps reasonable (300 for smoke, 1000 for train, then monitor eval)
- [ ] VRAM within T4 limits (~15GB total, LoRA helps if moving to 7B base)
- [ ] Baseline measured (loss at step 1 vs. last step)
- [ ] New RUN_NAME for this run (overwrite protection)

## Clyde's Tool-Use Guarantees (After Training)
1. **Never hallucinate a command** — if unsure, say "I couldn't verify this from training data"
2. **Always cite sources** — every answer includes `Source: <sources>`
3. **Correct common mistakes** — e.g., `dir` → `ls` on Linux, wrong flags → correct flags
4. **Know boundaries** — "For Raspberry Pi specifically, try `vcgencmd measure_temp`; for generic Linux, `cat /sys/class/thermal/thermal_zone0/temp`"
5. **Provide alternatives** — when one command has caveats, offer working alternatives with their own source notes
