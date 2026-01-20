# Duet LLM

Duet LLM is a framework for running multi-agent conversations between LLMs. It supports both local models via Ollama and cloud models via the Anthropic API.

**Designed for:**
- Running two personas against each other (e.g., skeptical physicist vs mystic panpsychist)
- Swapping personas and models via CLI flags
- Optional judge/referee and user persona that interject periodically
- Saving the full discussion as a markdown log
- Mixing local and cloud models

---

## Features

- **Dual provider support** - Run conversations on local Ollama models or Anthropic Claude models
- **Persona system** - Markdown files with Name/ShortName headers define agent personalities
- **Per-agent models** - Agent A and B can use different models (even different providers in future)
- **Optional judge agent** - A third agent that critiques the dialogue at intervals
- **Optional user persona** - Your voice that jumps in periodically
- **Markdown logging** - Full conversation saved to `logs/`
- **Flexible CLI** - Control personas, models, intervals, max turns, and more

---

## Requirements

- macOS or Linux
- Python 3.10+

**For local models (Ollama):**
- [Ollama](https://ollama.ai) installed and running
- At least one model pulled (e.g., `ollama pull mistral`)

**For cloud models (Anthropic):**
- Anthropic API key
- `anthropic` Python package

---

## Installation

Clone the repo:

```bash
git clone https://github.com/kcdjmaxx/llm-duet.git
cd llm-duet
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

For Ollama, make sure you have a model installed:

```bash
ollama pull mistral
```

For Anthropic, set your API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Quick Start

Run a conversation with default settings (Ollama + Mistral):

```bash
python duet.py
```

You'll be prompted for a topic:

```
Enter start topic (word or full prompt):
```

The agents will then talk autonomously. Stop anytime with `Ctrl-C`.

Logs are saved in `logs/`.

---

## Providers

### Ollama (Local)

Default provider. Runs models locally on your machine.

```bash
python duet.py -m mistral
python duet.py -m llama3.2
python duet.py -m qwen2.5:7b
```

Set a custom Ollama endpoint:

```bash
export OLLAMA_URL="http://localhost:11434/api/chat"
```

### Anthropic (Cloud)

Use Claude models via the Anthropic API.

```bash
# Claude Haiku (fast, cheap - good for testing)
python duet.py --provider anthropic

# Claude Sonnet (balanced)
python duet.py --provider anthropic --anthropic-model claude-sonnet-4-20250514

# Claude Opus (most capable)
python duet.py --provider anthropic --anthropic-model claude-opus-4-20250514
```

Different models per agent:

```bash
python duet.py --provider anthropic \
  --anthropic-model-a claude-haiku-4-5-20251001 \
  --anthropic-model-b claude-sonnet-4-20250514
```

---

## Persona Files

Personas live in `personas/` as Markdown files. Each must begin with:

```markdown
Name: Full Display Name
ShortName: ShortTag
```

Example (`personas/agent_a.md`):

```markdown
Name: Dr. Lena Hart
ShortName: Hart

# Persona Overview
A skeptical physicist who demands empirical evidence...

## Core Traits
- Analytical and precise
- Questions assumptions
- Values reproducibility

## Expressive Gears
### 1. Rational Mode
Calm, methodical analysis...

### 2. Passionate Mode
Animated defense of scientific method...
```

The rest of the file is free-form system prompt content that shapes the agent's personality.

### Creating Personas

Use the interactive persona generator:

```bash
python personaGen.py
```

This walks you through worldview, traits, gears, role, quirks, and mission.

---

## CLI Reference

```bash
python duet.py --help
```

### Core Options

| Flag | Description | Default |
|------|-------------|---------|
| `-A, --agentA` | Persona file for Agent A | `personas/agent_a.md` |
| `-B, --agentB` | Persona file for Agent B | `personas/agent_b.md` |
| `-m, --model` | Default Ollama model for both agents | `mistral` |
| `-MA, --modelA` | Ollama model override for Agent A | None |
| `-MB, --modelB` | Ollama model override for Agent B | None |

### Provider Options

| Flag | Description | Default |
|------|-------------|---------|
| `--provider` | LLM provider (`ollama` or `anthropic`) | `ollama` |
| `--anthropic-model` | Default Anthropic model for both agents | `claude-haiku-4-5-20251001` |
| `--anthropic-model-a` | Anthropic model override for Agent A | None |
| `--anthropic-model-b` | Anthropic model override for Agent B | None |

### Judge Options

| Flag | Description | Default |
|------|-------------|---------|
| `--judge-persona` | Persona file for judge/referee agent | None |
| `--judge-model` | Ollama model for judge | Same as `--model` |
| `--judge-interval` | Judge comments every N turns (0 = disabled) | `0` |

### User Persona Options

| Flag | Description | Default |
|------|-------------|---------|
| `--user-persona` | Persona file representing you | None |
| `--user-interval` | User persona interjects every N turns (0 = disabled) | `0` |

### Other Options

| Flag | Description | Default |
|------|-------------|---------|
| `--max-turns` | Stop after N A/B exchanges (0 = infinite) | `0` |
| `--logfile` | Custom log file path | Auto-generated in `logs/` |
| `--no-color` | Disable colored terminal output | `false` |

---

## Examples

### Basic Usage

```bash
# Default (Ollama + Mistral)
python duet.py

# Specific Ollama model
python duet.py -m llama3.2

# Different models per agent
python duet.py -MA mistral -MB qwen2.5:7b
```

### Using Claude

```bash
# Claude Haiku (default)
python duet.py --provider anthropic

# Claude Sonnet
python duet.py --provider anthropic --anthropic-model claude-sonnet-4-20250514

# Mixed Claude models
python duet.py --provider anthropic \
  --anthropic-model-a claude-haiku-4-5-20251001 \
  --anthropic-model-b claude-sonnet-4-20250514
```

### With Judge

```bash
# Judge comments every 4 turns
python duet.py \
  --judge-persona personas/judge.md \
  --judge-interval 4
```

### With User Persona

```bash
# Your persona interjects every 3 turns
python duet.py \
  --user-persona personas/agent_user.md \
  --user-interval 3
```

### Full Example

```bash
python duet.py \
  -A personas/agent_a.md \
  -B personas/agent_b.md \
  --provider anthropic \
  --anthropic-model claude-sonnet-4-20250514 \
  --judge-persona personas/judge.md \
  --judge-interval 5 \
  --max-turns 20 \
  --logfile logs/debate.md
```

### Limit Conversation Length

```bash
python duet.py --max-turns 10
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_URL` | Ollama API endpoint | `http://localhost:11434/api/chat` |
| `ANTHROPIC_API_KEY` | Anthropic API key (required for `--provider anthropic`) | None |

---

## Project Structure

```
duet_llm/
├── duet.py           # Main orchestrator
├── personaGen.py     # Interactive persona builder
├── personas/         # Persona markdown files
│   ├── agent_a.md
│   ├── agent_b.md
│   ├── judge.md
│   └── ...
├── logs/             # Conversation transcripts (auto-generated)
├── requirements.txt  # Python dependencies
└── README.md
```

---

## License

MIT License. See LICENSE for details.
