# Anthropic/Claude Integration Plan

**Status:** Sketched out, ready to implement
**Date:** 2026-01-19

## Summary

Add support for frontier models (Claude Haiku, Sonnet, Opus) alongside existing Ollama backend. This would allow higher-quality conversations and mix-and-match between local and cloud models.

## Why

- Local models (wizardlm, qwen, mistral) have quirks:
  - wizardlm generates both sides of conversation in one turn
  - Models overuse filler phrases ("interesting", "great point")
  - Struggle to follow brevity guidelines
- Claude models follow instructions more reliably
- Haiku is cheap/fast, good for experimentation
- Could mix providers (Agent A on Haiku, Agent B on local)

## Architecture

The current design already works well:
- Persona markdown → system prompt (Claude supports this natively)
- Separate conversation histories per agent (no change needed)
- Turn-based loop (no change needed)

Main change: abstract the chat call to support multiple providers.

## Implementation Sketch

### 1. New imports (top of duet.py)
```python
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
```

### 2. New CLI args
```python
parser.add_argument(
    "--provider",
    choices=["ollama", "anthropic"],
    default="ollama",
    help="LLM provider to use.",
)

parser.add_argument(
    "--anthropic-model",
    default="claude-3-haiku-20240307",
    help="Anthropic model ID.",
)
```

### 3. New chat function for Claude
```python
def chat_with_claude(model_name, system_prompt, messages, max_tokens=250):
    client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var
    response = client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text
```

### 4. Provider-agnostic wrapper
```python
def chat(provider, ollama_url, ollama_model, anthropic_model, system_prompt, messages):
    if provider == "anthropic":
        if not HAS_ANTHROPIC:
            raise RuntimeError("anthropic package not installed")
        # Claude takes system separately, filter it out of messages
        user_assistant_msgs = [m for m in messages if m["role"] != "system"]
        return chat_with_claude(anthropic_model, system_prompt, user_assistant_msgs)
    else:
        return chat_with_model(ollama_url, ollama_model, messages)
```

### 5. Track system prompts as strings

Store `system_prompt_a` and `system_prompt_b` as strings (for Anthropic), while still building message lists with system role (for Ollama compatibility).

### 6. Update all chat calls

Replace:
```python
a_reply = chat_with_model(ollama_url, model_a, conversation_a)
```

With:
```python
a_reply = chat(
    args.provider, ollama_url, model_a,
    args.anthropic_model, system_prompt_a, conversation_a
)
```

### 7. Update requirements.txt
```
requests
anthropic>=0.18.0
```

## Usage Examples

```bash
# Local Ollama (unchanged)
python duet.py -m mistral

# Claude Haiku
python duet.py --provider anthropic --anthropic-model claude-3-haiku-20240307

# Claude Sonnet
python duet.py --provider anthropic --anthropic-model claude-3-5-sonnet-20241022
```

## Future Enhancements

- Per-agent Anthropic model selection (`--anthropic-model-a`, `--anthropic-model-b`)
- Mix providers (Agent A on Claude, Agent B on Ollama)
- Token/cost tracking for Anthropic calls

## Environment Setup

Will need:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
pip install anthropic
```

## Changes Made This Session

Before implementing Anthropic, we improved conversational quality:

1. **num_predict: 250** - Bumped from 150 to avoid mid-sentence cutoffs
2. **temperature: 0.8** - Slightly higher for natural variation
3. **Conversation guidelines** added to system prompts:
   - Keep responses 1-3 sentences
   - React before explaining
   - No formal transitions or sign-offs
   - No filler phrases ("interesting", "great point")
   - No numbered lists or headers

These changes are in the working tree (not committed).
