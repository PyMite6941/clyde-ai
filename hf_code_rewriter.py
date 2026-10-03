"""
hf_code_rewriter.py
-------------------
Same architecture as tiny_gpt_walkthrough.py, but with PRETRAINED weights
from Hugging Face. This is the file that can actually rewrite buggy code.

Install once:
    pip install torch transformers

Run:
    python hf_code_rewriter.py

First run downloads the model into your Hugging Face cache
(usually ~/.cache/huggingface). After that it works offline.
"""

from __future__ import annotations

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


# A small instruct-tuned coder. Swap this string if you have more RAM:
#   "Qwen/Qwen2.5-Coder-0.5B-Instruct"   ~1 GB  (this default)
#   "Qwen/Qwen2.5-Coder-1.5B-Instruct"   ~3 GB
#   "Qwen/Qwen2.5-Coder-3B-Instruct"     ~6 GB
#   "Qwen/Qwen2.5-Coder-7B-Instruct"     ~15 GB
MODEL_ID = "Qwen/Qwen2.5-Coder-0.5B-Instruct"

# Generation numbers — see comments in generate_rewrite()
MAX_NEW_TOKENS = 256
TEMPERATURE = 0.2
TOP_P = 0.9
TOP_K = 50
REPETITION_PENALTY = 1.05


def load_model(model_id: str = MODEL_ID):
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    model.eval()
    device = next(model.parameters()).device
    print(f"loaded {model_id}")
    print(f"device={device}  dtype={dtype}")
    print(f"layers={model.config.num_hidden_layers}  "
          f"hidden={model.config.hidden_size}  "
          f"heads={model.config.num_attention_heads}  "
          f"vocab={model.config.vocab_size}  "
          f"ctx={model.config.max_position_embeddings}")
    return tokenizer, model, device


def build_messages(buggy_code: str, language: str, expected: str) -> list[dict]:
    """Chat models expect a list of role/content dicts, not a raw string."""
    system = (
        "You are a careful programming tutor. "
        "Find the bug, explain it in 3 short bullets, then print the "
        "full corrected code only. Do not add extra features."
    )
    user = (
        f"Language: {language}\n"
        f"Expected behavior: {expected}\n"
        f"Buggy code:\n```{language}\n{buggy_code}\n```"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


@torch.no_grad()
def generate_rewrite(
    tokenizer,
    model,
    device,
    buggy_code: str,
    language: str = "python",
    expected: str = "the function should do what its name says",
) -> str:
    messages = build_messages(buggy_code, language, expected)
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    # What each number does:
    #   max_new_tokens     hard cap on how long the answer can be
    #   temperature        0.0-0.3 = precise bugfixes; 0.8+ = more inventive
    #   top_p              nucleus: keep the smallest set of tokens whose
    #                      probabilities sum to p. 0.9 is a common default.
    #   top_k              extra cap: never consider more than K tokens
    #   repetition_penalty >1.0 slightly punishes repeating the same lines
    #   do_sample          False + temp ignored = greedy (always top token)
    output_ids = model.generate(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        top_k=TOP_K,
        repetition_penalty=REPETITION_PENALTY,
        do_sample=TEMPERATURE > 0,
        pad_token_id=tokenizer.eos_token_id,
    )
    new_tokens = output_ids[0, inputs["input_ids"].shape[1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


BUGGY = """
def factorial(n):
    result = 1
    for i in range(n):
        result *= i
    return result
"""


if __name__ == "__main__":
    tokenizer, model, device = load_model()
    text = generate_rewrite(
        tokenizer,
        model,
        device,
        buggy_code=BUGGY,
        language="python",
        expected="factorial(5) should return 120",
    )
    print("\n===== MODEL OUTPUT =====\n")
    print(text)
