"""
tiny_gpt_walkthrough.py
-----------------------
A readable, from-scratch GPT-style language model in raw PyTorch.

Run:
    python tiny_gpt_walkthrough.py

What this file is for
    Understand shapes, layers, and how hyperparameter NUMBERS change
    the network. This tiny model will NOT write good code by itself.
    A useful coding chatbot still needs PRETRAINED weights (see the
    second half of this file and the companion explanation).

Shape convention used everywhere:
    B = batch size          (how many examples at once)
    T = sequence length     (how many tokens in the context)
    C = n_embd              (width of one token vector)
    V = vocab_size          (how many distinct tokens exist)
    H = n_head              (how many attention heads)
    D = head_dim = C // H   (width of one head)
"""

from __future__ import annotations

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


# =============================================================================
# 1. HYPERPARAMETERS — these numbers ARE the model
# =============================================================================
# Change one number, re-run, and watch parameter count + tensor shapes change.

vocab_size = 200        # V. Tiny fake vocab. Real Qwen/GPT-2 is 50k–150k+.
block_size = 32         # T max. How far back the model can look.
n_embd = 64             # C. Width of every token vector.
n_head = 4              # H. Must divide n_embd evenly. 64 / 4 = 16.
n_layer = 2             # How many transformer blocks stacked.
dropout = 0.1           # Randomly zero 10% of values during TRAINING only.
bias = True             # Extra learnable offset in Linear / LayerNorm.

# Training-only knobs (used in the demo loop at the bottom)
batch_size = 8
learning_rate = 3e-4    # 0.0003 is a common AdamW starting point for small LMs
max_steps = 200         # Tiny demo. Real pretraining is millions of steps.

assert n_embd % n_head == 0, "n_embd must be divisible by n_head"
head_dim = n_embd // n_head  # D = 16 with the numbers above


# =============================================================================
# 2. TOKENIZER STAND-IN
# =============================================================================
# A real chatbot uses a subword tokenizer (BPE / SentencePiece).
# Those map "rewrite" -> one or a few integer IDs.
# Here we use character-level IDs so you can SEE the integers.

chars = (
    "\n "
    + "abcdefghijklmnopqrstuvwxyz"
    + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    + "0123456789"
    + "()[]{}.,:;=_+-*/<>!?#\"'\\"
)
# Keep vocab_size as the source of truth: pad / truncate the charset.
chars = (chars + "?" * vocab_size)[:vocab_size]
stoi = {ch: i for i, ch in enumerate(chars)}
itos = {i: ch for ch, i in stoi.items()}


def encode(text: str) -> list[int]:
    """String -> list of integer token IDs. Unknown chars become 0."""
    return [stoi.get(ch, 0) for ch in text]


def decode(ids: list[int] | torch.Tensor) -> str:
    """Integer token IDs -> string."""
    if isinstance(ids, torch.Tensor):
        ids = ids.tolist()
    return "".join(itos.get(int(i), "?") for i in ids)


# =============================================================================
# 3. BUILDING BLOCKS
# =============================================================================

class CausalSelfAttention(nn.Module):
    """
    One attention layer.

    For every token t, the model builds a weighted average of ALL tokens
    at positions <= t (never the future — that is the "causal" mask).

    With our demo numbers:
        x comes in as        (B, T, 64)
        q, k, v after split  (B, 4, T, 16)   # 4 heads, each 16-wide
        attn scores          (B, 4, T, T)    # every token vs every token
        output               (B, T, 64)      # same shape as input
    """

    def __init__(self):
        super().__init__()
        # One matrix produces Q, K, V concatenated: 3 * n_embd outputs.
        self.c_attn = nn.Linear(n_embd, 3 * n_embd, bias=bias)
        # Mix the heads back together after attention.
        self.c_proj = nn.Linear(n_embd, n_embd, bias=bias)
        self.attn_drop = nn.Dropout(dropout)
        self.resid_drop = nn.Dropout(dropout)

        # Lower-triangular mask: 1 means "allowed to look", 0 means "blocked".
        # Registered as a buffer so it moves to GPU with the model
        # but is NOT a trainable parameter.
        mask = torch.tril(torch.ones(block_size, block_size))
        self.register_buffer("mask", mask.view(1, 1, block_size, block_size))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape  # e.g. (8, 32, 64)

        qkv = self.c_attn(x)                          # (B, T, 192)
        q, k, v = qkv.split(n_embd, dim=-1)           # each (B, T, 64)

        # Reshape into heads: (B, T, H, D) then swap to (B, H, T, D)
        q = q.view(B, T, n_head, head_dim).transpose(1, 2)
        k = k.view(B, T, n_head, head_dim).transpose(1, 2)
        v = v.view(B, T, n_head, head_dim).transpose(1, 2)

        # Scaled dot-product attention.
        # Divide by sqrt(D) so the dot products don't explode as D grows.
        # D=16 -> scale = 4.0
        att = (q @ k.transpose(-2, -1)) / math.sqrt(head_dim)  # (B, H, T, T)
        att = att.masked_fill(self.mask[:, :, :T, :T] == 0, float("-inf"))
        att = F.softmax(att, dim=-1)  # each row sums to 1.0
        att = self.attn_drop(att)

        y = att @ v                                   # (B, H, T, D)
        y = y.transpose(1, 2).contiguous().view(B, T, C)  # (B, T, 64)
        y = self.resid_drop(self.c_proj(y))
        return y


class MLP(nn.Module):
    """
    Feed-forward network applied independently to each token.

    Classic GPT width: expand to 4 * n_embd, GELU, project back.
    With n_embd=64 that is 64 -> 256 -> 64.

    Why expand? Attention mixes INFORMATION ACROSS TOKENS.
    The MLP lets each token THINK HARDER about what it just saw.
    """

    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(n_embd, 4 * n_embd, bias=bias)
        self.proj = nn.Linear(4 * n_embd, n_embd, bias=bias)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc(x)
        x = F.gelu(x)
        x = self.proj(x)
        x = self.drop(x)
        return x


class Block(nn.Module):
    """
    One transformer block = Pre-Norm + Attention + residual
                            + Pre-Norm + MLP      + residual

    Residual connections (x + sublayer(x)) are why we can stack
    many layers without the signal vanishing.
    """

    def __init__(self):
        super().__init__()
        self.ln1 = nn.LayerNorm(n_embd)
        self.attn = CausalSelfAttention()
        self.ln2 = nn.LayerNorm(n_embd)
        self.mlp = MLP()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        x = x + self.mlp(self.ln2(x))
        return x


class TinyGPT(nn.Module):
    """
    Full causal language model.

    Forward returns:
        logits: (B, T, V)  score for every vocab item at every position
        loss:   scalar     how wrong the next-token guesses were (or None)
    """

    def __init__(self):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, n_embd)   # (V, C)
        self.pos_emb = nn.Embedding(block_size, n_embd)   # (Tmax, C)
        self.drop = nn.Dropout(dropout)
        self.blocks = nn.ModuleList([Block() for _ in range(n_layer)])
        self.ln_f = nn.LayerNorm(n_embd)
        self.lm_head = nn.Linear(n_embd, vocab_size, bias=False)

        # Weight tying: the same matrix that looks up token vectors
        # is reused to predict tokens. Saves params and often helps quality.
        self.lm_head.weight = self.tok_emb.weight

        self.apply(self._init_weights)

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx: torch.Tensor, targets: torch.Tensor | None = None):
        B, T = idx.shape
        if T > block_size:
            raise ValueError(f"Sequence length {T} exceeds block_size {block_size}")

        token_vectors = self.tok_emb(idx)                         # (B, T, C)
        positions = torch.arange(T, device=idx.device)
        position_vectors = self.pos_emb(positions)[None, :, :]    # (1, T, C)
        x = self.drop(token_vectors + position_vectors)

        for block in self.blocks:
            x = block(x)

        x = self.ln_f(x)
        logits = self.lm_head(x)                                  # (B, T, V)

        loss = None
        if targets is not None:
            # Flatten to (B*T, V) vs (B*T,) — standard next-token CE loss.
            loss = F.cross_entropy(
                logits.view(-1, vocab_size),
                targets.view(-1),
            )
        return logits, loss

    @torch.no_grad()
    def generate(
        self,
        idx: torch.Tensor,
        max_new_tokens: int,
        temperature: float = 1.0,
        top_k: int | None = 20,
    ) -> torch.Tensor:
        """
        Autoregressive decode: predict one token, append it, repeat.

        temperature
            0.2  = almost always pick the top token (safe, repetitive)
            1.0  = sample from the model's real distribution
            1.5  = flatter distribution, more surprising / sloppy
        top_k
            keep only the K most likely tokens before sampling.
            Smaller K = safer. None = use the full vocab.
        """
        self.eval()
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -block_size:]          # never exceed context
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :] / max(temperature, 1e-6)

            if top_k is not None:
                values, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                cutoff = values[:, [-1]]
                logits = logits.masked_fill(logits < cutoff, float("-inf"))

            probs = F.softmax(logits, dim=-1)        # (B, V), sums to 1
            next_id = torch.multinomial(probs, num_samples=1)
            idx = torch.cat([idx, next_id], dim=1)
        return idx


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


# =============================================================================
# 4. DEMO: shapes, a few train steps, then generate
# =============================================================================

def print_shapes(model: TinyGPT) -> None:
    print("\n=== Tensor shapes with the demo numbers ===")
    print(f"vocab_size={vocab_size}  block_size={block_size}  "
          f"n_embd={n_embd}  n_head={n_head}  n_layer={n_layer}")
    print(f"head_dim = n_embd / n_head = {head_dim}")
    print(f"trainable parameters = {count_parameters(model):,}")

    idx = torch.randint(0, vocab_size, (batch_size, block_size))
    logits, loss = model(idx, targets=idx)
    print(f"input idx     {tuple(idx.shape)}     # (B, T)")
    print(f"token embed   ({batch_size}, {block_size}, {n_embd})")
    print(f"attention     ({batch_size}, {n_head}, {block_size}, {block_size})")
    print(f"logits        {tuple(logits.shape)}  # (B, T, V)")
    print(f"demo loss     {loss.item():.4f}  (random init ≈ ln(V) ≈ {math.log(vocab_size):.2f})")


def make_batch(text: str, B: int, T: int) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Language-model batch: predict the NEXT character.
        x = tokens[0 : T]
        y = tokens[1 : T+1]
    """
    data = torch.tensor(encode(text), dtype=torch.long)
    if data.numel() <= T + 1:
        raise ValueError("Training text is too short for this block_size.")
    ix = torch.randint(0, data.numel() - T - 1, (B,))
    x = torch.stack([data[i : i + T] for i in ix])
    y = torch.stack([data[i + 1 : i + T + 1] for i in ix])
    return x, y


TRAIN_TEXT = """
def add(a, b):
    return a + b

def broken_add(a, b):
    return a - b

# bug: used minus instead of plus
# fix: return a + b
"""


def demo_train_and_generate() -> None:
    torch.manual_seed(42)
    model = TinyGPT()
    print_shapes(model)

    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    model.train()
    print("\n=== Training a few steps on a tiny string (not enough to learn code) ===")
    for step in range(1, max_steps + 1):
        x, y = make_batch(TRAIN_TEXT, batch_size, block_size)
        _, loss = model(x, y)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        if step == 1 or step % 50 == 0:
            print(f"step {step:4d}  loss={loss.item():.4f}")

    prompt = "def add"
    start = torch.tensor([encode(prompt)], dtype=torch.long)
    print("\n=== Generation at three temperatures ===")
    for temp in (0.2, 1.0, 1.5):
        out = model.generate(start.clone(), max_new_tokens=40, temperature=temp, top_k=20)
        print(f"temp={temp!s:<3} -> {decode(out[0])!r}")


if __name__ == "__main__":
    demo_train_and_generate()
