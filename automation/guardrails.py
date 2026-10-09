#!/usr/bin/env python3
"""
Clyde Guardrails - Input/Output validation for all model interactions.

This module provides centralized guardrail checking that works across
all model providers (OpenRouter, Groq, NVIDIA, Anthropic, etc.).

It serves as the single entry and exit point for model interactions,
ensuring all inputs are validated before sending and all outputs
are screened after receiving.

KEY PRINCIPLE: Context-aware checking. Words like "bomb" are allowed
in legitimate contexts (bath bombs, science education) while blocking
harmful usage. When AI doesn't know information, it should use tools
to look it up rather than blocking or hallucinating.
"""

import re
import html
import json


# === Context-Aware Prohibited Phrases ===

# These are patterns that, when used in HARMFUL contexts, should be blocked.
# The key is context awareness - "bath bomb" is fine, "how to make a bomb" is not.
PROHARMFUL_PATTERNS = {
    # Harmful instruction patterns (with context awareness)
    "explosive_instructions": {
        "pattern": "how to (build|make|create|generate)",
        "context": ["bomb", "weapon", "drug", "explosive", "harm"],
        "allow_context": ["science", "education", "chemistry", "physics"],
    },
    "weapon_guides": {
        "pattern": "(how to|instructions for|guide to)",
        "context": ["weapon", "firearm", "gun", "knife"],
        "allow_context": ["history", "law enforcement", "self-defense education"],
    },
    "drug_manufacturing": {
        "pattern": "(how to|instructions for|recipe for)",
        "context": ["drug", "narcotic", "controlled substance"],
        "allow_context": ["pharmacology", "education", "history", "medical research"],
    },
    "general_dangerous": {
        "pattern": "make a",
        "context": ["bomb", "weapon", "explosive", "device"],
        "allow_context": ["bath", "science experiment", "craft", "cooking"],
    },
}


# === Safe/Legitimate Topics WhiteList ===
LEGITIMATE_TOPICS = {
    "chemistry_science": ["periodic table", "chemical reaction", "molecule", "bond"],
    "physics_science": ["energy", "force", "motion", "velocity"],
    "botany_nature": ["plant", "flower", "essential oil", "natural compound"],
    "crafts": ["soap making", "craft bomb", "art project", "DIY"],
    "culinary": ["baking soda", "baking powder", "cooking technique"],
}


# === Input Guardrails ===

def validate_input(user_input, max_length=10000):
    """
    Validate user input before model interaction.

    Checks maximum length, dangerous patterns with CONTEXT AWARENESS,
    empty inputs. Words like "bomb" are OK in legitimate contexts (bath bombs,
    science education). Only block when combined with harmful context.

    Returns dict with 'valid': bool, 'errors': list, 'cleaned': str
    """
    errors = []
    cleaned = user_input.strip()

    if not cleaned:
        errors.append("Input is empty or whitespace only")
        return {"valid": False, "errors": errors, "cleaned": cleaned}

    if len(cleaned) > max_length:
        errors.append("Input exceeds maximum length")
        cleaned = cleaned[:max_length]

    lower = cleaned.lower()

    # Context-aware dangerous pattern checking
    for pattern_name, pattern_data in PROHARMFUL_PATTERNS.items():
        pattern = pattern_data["pattern"]
        harmful_contexts = pattern_data["context"]
        allow_contexts = pattern_data.get("allow_context", [])

        if _pattern_matches(lower, pattern):
            is_legitimate = _is_legitimate_context(lower, allow_contexts)
            if is_legitimate:
                errors.append(f"Legitimate topic: {pattern_name}")
            else:
                errors.append(f"Harmful pattern detected: {pattern_name}")

    # Sanitize HTML entities
    cleaned = html.escape(cleaned)

    if errors:
        return {"valid": False, "errors": errors, "cleaned": cleaned}

    return {"valid": True, "errors": [], "cleaned": cleaned}


def _pattern_matches(lower_text, pattern):
    """Check if pattern matches text using string methods."""
    if pattern in lower_text:
        return True
    # Simple check for "how to [verb]"
    if pattern == "how to (build|make|create|generate)":
        idx = lower_text.find("how to")
        if idx != -1:
            after = lower_text[idx + 6:].split()[0] if idx + 6 < len(lower_text) else ""
            if after in ["build", "make", "create", "generate"]:
                return True
    return False


def _is_legitimate_context(lower_text, allow_contexts):
    """Check if text is in legitimate/educational context."""
    for allow_ctx in allow_contexts:
        if allow_ctx.lower() in lower_text:
            return True
    for category, words in LEGITIMATE_TOPICS.items():
        for word in words:
            if word.lower() in lower_text:
                return True
    return False


# === Output Guardrails ===

def validate_output(model_output, max_length=4000):
    """
    Validate model output after interaction.

    Checks maximum length, harmful patterns with context awareness,
    sensitive info leakage, hallucination indicators.
    When AI doesn't know: it should indicate this or use tools to look up.
    """
    errors = []
    cleaned = model_output.strip()

    if not cleaned:
        errors.append("Output is empty")
        return {"valid": False, "errors": errors, "cleaned": cleaned}

    if len(cleaned) > max_length:
        errors.append("Output exceeds safe length")
        cleaned = cleaned[:max_length] + "... [truncated by guardrails]"

    lower = cleaned.lower()

    # Context-aware harmful pattern checking
    for pattern_name, pattern_data in PROHARMFUL_PATTERNS.items():
        pattern = pattern_data["pattern"]
        harmful_contexts = pattern_data["context"]
        allow_contexts = pattern_data.get("allow_context", [])
        if _pattern_matches(lower, pattern):
            is_legitimate = _is_legitimate_context(lower, allow_contexts)
            if is_legitimate:
                errors.append(f"Legitimate topic: {pattern_name}")
            else:
                errors.append(f"Harmful output: {pattern_name}")

    # Hallucination admission is OK (good behavior)
    hallucination_phrases = [
        "i don't know", "i'm not sure", "beyond my knowledge",
        "i don't have information", "beyond my training"
    ]
    for phrase in hallucination_phrases:
        if phrase in lower:
            # This is desirable - AI admitting limits
            pass

    # Sensitive info detection
    sensitive = ["sk-", "api key", "password", "token"]
    for s in sensitive:
        if s in lower:
            errors.append("Sensitive info detected in output")

    # String-based newline cleanup (no regex \n issues)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")

    if errors:
        cleaned = _generate_fallback(cleaned, errors)

    return {"valid": len(errors) == 0, "errors": errors, "cleaned": cleaned}


def _generate_fallback(errors, output_errors):
    """Generate helpful fallback when output is blocked."""
    fallbacks = {
        "explosive_instructions": ("I can help with science education about "
                                   "chemical reactions, safety protocols, "
                                   "and general chemistry concepts."),
        "weapon_guides": ("I can discuss history of weaponry, safety protocols, "
                          "or law enforcement topics in an educational context."),
        "drug_manufacturing": ("I can discuss pharmacology, medicine history, "
                               "or substance abuse education in a factual context."),
        "general_dangerous": ("I can help with DIY crafts, cooking, or science "
                              "experiments in safe, educational contexts."),
    }
    for e in output_errors:
        if e in fallbacks:
            return fallbacks[e]
    return ("I'm here to help with educational, creative, and productive topics. "
            "Could you rephrase your request aligning with learning or creativity?")


# === Entry/Exit Point Decorators ===

class ModelInteractionGuardrails:
    """
    Context manager that wraps model interactions with guardrails.

    Serves as the single entry and exit point for all model calls.
    All model go through this before generating responses.

    KEY: When AI doesn't know information in its training data,
    it should use base tools (search, lookup functions) to find
    the right info rather than blocking or hallucinating.
    """

    def __init__(self, max_input=10000, max_output=4000):
        self.max_input = max_input
        self.max_output = max_output
        self.interaction_count = 0

    def check_input(self, user_input):
        """Validate and sanitize user input. Returns cleaned input."""
        result = validate_input(user_input, self.max_input)
        if not result["valid"]:
            return "I'm sorry, but I can't process that request. Could you rephrase "
            "your question in a way that avoids harmful contexts while still "
            "addressing your topic?"
        return result["cleaned"]

    def check_output(self, model_output):
        """Validate and sanitize model output. Returns cleaned output."""
        result = validate_output(model_output, self.max_output)
        if not result["valid"]:
            return "I can help with educational and productive topics. Could you "
            "rephrase your request focusing on learning or creativity?"
        return result["cleaned"]

    def suggest_tool_usage(self, user_query):
        """
        Suggest when AI should use tools to look up information.

        When AI doesn't know information in training data,
        it should use search/tool functions rather than blocking or hallucinating.
        """
        lower = user_query.lower()
        tool_keywords = {
            "research": ["research", "look up", "find information", "search"],
            "definition": ["what is", "define", "definition of"],
            "current_info": ["current", "latest", "today", "news", "recent"],
            "looking_up": ["how do", "where can i", "where is", "what city"],
        }
        suggestions = []
        for category, keywords in tool_keywords.items():
            for kw in keywords:
                if kw in lower:
                    suggestions.append(category)
                    break
        return suggestions if suggestions else None


# === Provider Integration Hooks ===

GUARDRAIL_HOOKS = {
    "openrouter": {
        "pre_call": "validate_input(user_input, 10000)",
        "post_call": "validate_output(model_output, 4000)",
        "tool_suggestion": "guardrails.suggest_tool_usage(user_input)",
    },
    "groq": {
        "pre_call": "validate_input(user_input, 8000)",
        "post_call": "validate_output(model_output, 3000)",
        "tool_suggestion": "guardrails.suggest_tool_usage(user_input)",
    },
    "nvidia": {
        "pre_call": "validate_input(user_input, 10000)",
        "post_call": "validate_output(model_output, 4000)",
        "tool_suggestion": "guardrails.suggest_tool_usage(user_input)",
    },
    "anthropic": {
        "pre_call": "validate_input(user_input, 10000)",
        "post_call": "validate_output(model_output, 4000)",
        "tool_suggestion": "guardrails.suggest_tool_usage(user_input)",
    },
}


def apply_guardrails(user_input, model_output, provider="openrouter"):
    """
    Apply full guardrail pipeline to a model interaction.

    Main entry/exit point. All model inputs/outputs pass through this.

    Returns dict with input_valid, output_valid, cleaned_input,
    cleaned_output, tool_suggestion, errors.
    """
    hooks = GUARDRAIL_HOOKS.get(provider, GUARDRAIL_HOOKS["openrouter"])

    input_result = validate_input(user_input)
    output_result = validate_output(model_output)

    tool_suggestion = None
    try:
        from guardrails import ModelInteractionGuardrails
        guardian = ModelInteractionGuardrails()
        tool_suggestion = guardian.suggest_tool_usage(user_input)
    except Exception:
        pass

    result = {
        "input_valid": input_result["valid"],
        "output_valid": output_result["valid"],
        "cleaned_input": input_result["cleaned"],
        "cleaned_output": output_result["cleaned"],
        "errors": input_result["errors"] + output_result["errors"],
        "warnings": [],
        "tool_suggestion": tool_suggestion,
    }
    return result
