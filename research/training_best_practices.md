# Clyde Research — LLM Training Best Practices (2026)

## Core Principle: Data Quality > Model Size > Hyperparameters

### 1. When to Fine-Tune vs. RAG/Prompting
- **Use RAG** when: model needs knowledge over private/docs/facts that change
- **Use fine-tuning** when: consistent style/format, domain-specific language, behavior changes, latency constraints
- **Rule of thumb**: 80% of "need fine-tuning" requests solved by better prompting/RAG first

### 2. Fine-Tuning Techniques (2026 defaults)
- **SFT** (Supervised Fine-Tuning): Train on (instruction, response) pairs
  - Minimal: 500 well-curated examples
  - Typical: 1-3 epochs, lr=2e-4, bf16
  - Format: Alpaca chat format or JSONL
  
- **LoRA** (Parameter-Efficient): Only train ~0.1-1% of weights
  - Default rank: r=32, alpha=64
  - Target: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
  - Fits 7B model on single A100/RTX 3090
  
- **QLoRA**: LoRA on 4-bit quantized base
  - 7B: ~6GB VRAM, 13B: ~10GB, 70B: ~48GB
  - Single consumer GPU achievable
  
- **DPO** (Direct Preference Optimization): Align with preferences, no reward model needed
  - Data format: (prompt, chosen, rejected) pairs
  - Usually after SFT: SFT → DPO pipeline
  - Beta parameter: 0.1-0.5 controls deviation from base
  - Cheaper/Stabler than RLHF (PPO)
  
- **ORPO**: Merges SFT + DPO into one stage
  - Simplest pipeline when you have preference data
  
- **KTO**: Binary feedback (thumbs up/down), no pairs needed
  - When you don't have pairwise comparisons

### 3. Data Preparation — The Real Quality Driver
- **Deduplication**: Remove exact/near-duplicate examples (causes memorization, not generalization)
- **Contamination check**: Ensure eval data NOT in training set (common cause of inflated metrics)
- **Quality filtering**: Remove low-quality/off-topic/contradictory examples
- **Length balance**: Pad to 95th percentile, not longest outlier
- **Stratified eval split**: By difficulty, category, protected attributes
- **Privacy**: PII redaction before training
- **Synthetic data**: Use stronger model to generate, then validate quality
  - Never train on synthetic data from same model (model collapse)
  - Standard practice: GPT-4o/Claude Sonnet to generate, human validate 10-20%

### 4. Training Best Practices
- **Learning rate**: 2e-4 (SFT), 5e-5 (DPO)
- **Epochs**: 1-3 typically; watch eval loss, stop if overfitting
- **Batch size**: 4-8 per device, gradient accumulation if needed
- **Optimizer**: paged_adamw_8bit, adamw_8bit, paged_adamw_32bit
- **Scheduler**: cosine decay with warmup
- **Max seq length**: 2048 typical; adjust to data

### 5. Evaluation Stack
- **Before training**: lm-evaluation-harness baseline on base model
- **After each checkpoint**: task-specific metrics (exact match, JSON validity, tool-call accuracy)
- **LLM-as-judge**: faithfulness, instruction following, tone
- **Human eval**: sampled review after each run
- **In production**: RAGAS for RAG quality, DeepEval as CI gate

### 6. Common Pitfalls to Avoid
- ❌ Fine-tuning to inject knowledge → Use RAG instead
- ❌ Wrong chat template → Train with correct template, verify 5 examples
- ❌ No eval before and after → Cannot diagnose forgetting without baselines
- ❌ Too many epochs (>3 on small data) → Watch eval loss, not train loss
- ❌ Adapter rank too low (r=4) → r=32 is fine default, saves no real memory, hurts quality
- ❌ Training fp16 on non-supporting hardware → Use bf16 on A100/H100
- ❌ Skipping DPO after SFT → SFT-only models produce correct but stylistically wrong outputs
- ❌ Serving in plain transformers → Use vLLM, TGI, or Triton for production

### 7. Recommended Default Pipeline (90% of cases)
```
1. Try prompting + few-shot (system prompt + 5-10 examples)
2. If not enough, try RAG (retrieval from your docs)
3. If still not enough quality/behavior → QLoRA on Llama 3.1 8B Instruct or Mistral 7B v0.3
4. If behavior needs refinement → DPO on preference pairs (1-5k hand-curated or LLM-judged)
5. Optional: RFT on verifiable tasks (math, code with tests)
```

### 8. Clyde-Specific Recommendations

Given your setup (Raspberry Pi / Kaggle T4 / limited VRAM):

**Baseline**: Track A (tiny GPT from scratch, no Qwen dependency)
- VRAM: ~2-4GB with N_embd=128, n_layer=2
- Best for: learning embeddings, attention mechanisms, tool-use patterns

**Recommended path**:
```
Phase 1: SFT on Q&A pairs (your 12+ rows + expanded)
  - Use LoRA if/when moving to larger base
  - Keep base weights frozen initially

Phase 2: DPO for "not yes-man" behavior
  - Need (prompt, chosen, rejected) pairs
  - Could start with synthetic rejections from base model
  - Beta=0.25 good default

Phase 3: If moving to 7B base (Llama 3.1 8B Instruct)
  - QLoRA on Kaggle (if quota allows) or OCI instance
  - Full pipeline: SFT → DPO → optional RFT
```

### 9. Storage Structure (Clyde/)
```
Clyde/
├── research/              ← research notes (this file + others)
│   ├── training_best_practices.md  ← this file
│   ├── qa_pairs_benchmark/     ← Gemini/ChatGPT generated pairs
│   ├── model_comparisons/      ← Track A vs others  
│   └── tool-use-scenarios/     ← real task examples
├── training_data/         ← stays in Clyde/
│   ├── sft.jsonl          ← Q&A pairs (your new data)
│   ├── eval.jsonl         ← hand-evaluated facts
│   └── packs/             ← pack definitions
├── runs/                  ← trained run folders
├── lab_log.md             ← experiment log
├── config.yaml            ← hyperparameters, pack configs
└── KAGGLE.md            ← upload instructions
```

### 10. Quick Quality Checklist Before Training
- [ ] Data deduplicated (no exact duplicates)
- [ ] Eval set held out (never seen by model)
- [ ] Chat template verified (print 5 training examples)
- [ ] Learning rate set (2e-4 for SFT, 5e-5 for DPO)
- [ ] Epochs reasonable (1-3, watch eval loss)
- [ ] VRAM within limits (T4: ~15GB, LoRA helps)
- [ ] Baseline measured (before/after metrics)
- [ ] No contamination between train/eval

---
*Last updated: 2026-09-30. Save to Clyde/research/training_best_practices.md for reference.*
