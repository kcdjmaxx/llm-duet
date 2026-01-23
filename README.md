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
- **Visual mode** - Live comic-style display with pygame for art installations
- **Ambient listening** - Microphone captures speech, influencing the conversation (art installation feature)
- **Icebreakers** - Structured topic rotation from markdown file, keeps conversation moving through curated topics

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

**For visual mode:**
- pygame
- Pillow (PIL)

**For ambient listening (--listen):**
- sounddevice
- faster-whisper
- numpy
- Microphone permissions granted to Terminal

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

### Visual Mode Options

| Flag | Description | Default |
|------|-------------|---------|
| `--visual` | Enable live comic-style visualization | `false` |
| `--visual-image` | Base image with speech balloons | `Artboard 1.png` |
| `--visual-pause` | Seconds to pause after each message | `3.0` |

### Ambient Listening & Icebreakers

| Flag | Description | Default |
|------|-------------|---------|
| `--listen` | Enable ambient listening (microphone input) | `false` |
| `--listen-interval` | Room whispers every N turns when topics are queued | `3` |
| `--whisper-model` | Whisper model size (tiny/base/small/medium/large) | `base` |
| `--topic-hold-turns` | How many turns to keep reinforcing a topic | `5` |
| `--icebreakers` | Path to icebreakers markdown file with topic list | None |

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

### Visual Mode

```bash
# Basic visual mode (uses Artboard 1.png)
python duet.py --provider anthropic --visual

# Custom image and longer reading time
python duet.py --provider anthropic --visual --visual-image myimage.png --visual-pause 5.0

# Recommended: Jamie & Riley with visual mode (art installation ready)
python duet.py --provider anthropic --visual --agentA personas/jamie.md --agentB personas/riley.md --visual-pause 6.0
```

### Ambient Listening (Art Installation)

```bash
# Enable microphone listening - conversation shifts based on what visitors say
python duet.py --provider anthropic --visual --listen --agentA personas/jamie.md --agentB personas/riley.md --visual-pause 6.0

# Longer topic persistence (8 turns instead of 5)
python duet.py --provider anthropic --visual --listen --topic-hold-turns 8

# Faster Whisper model for quicker transcription
python duet.py --provider anthropic --listen --whisper-model small
```

**How it works:**
1. Microphone captures ambient speech
2. Whisper transcribes speech to text
3. Topics queue up and are introduced by "The Room" persona
4. Topics persist for N turns, with reinforcement nudges
5. After N turns, the next queued topic is introduced

### Icebreakers (Structured Topic Rotation)

Icebreakers cycle through a curated list of topics, keeping conversations moving through specific subjects. Perfect for art installations, demos, or structured debates.

**Create an icebreakers file** (`iceBreakers.md`):
```markdown
---
rounds_per_topic: 4
---

# Ice Breaker Topics

1. What's the most overrated technology?
2. Should AI have rights?
3. Is consciousness computation?
4. Can art be objective?
5. What's the weirdest law of physics?
```

**Basic usage:**
```bash
# Use icebreakers to guide conversation
python duet.py --provider anthropic --icebreakers iceBreakers.md
```

**Controlling topic change speed:**

```bash
# Slow, natural drift (topics change gradually)
python duet.py --provider anthropic --icebreakers iceBreakers.md \
  --listen-interval 5 \
  --topic-hold-turns 8

# Fast topic hopping (quick shifts)
python duet.py --provider anthropic --icebreakers iceBreakers.md \
  --listen-interval 2 \
  --topic-hold-turns 3

# Very gradual (good for long art installations)
python duet.py --provider anthropic --icebreakers iceBreakers.md \
  --listen-interval 6 \
  --topic-hold-turns 10
```

**Combine with ambient listening:**
```bash
# Both icebreakers and microphone feed the same topic queue
python duet.py --provider anthropic --visual \
  --icebreakers iceBreakers.md \
  --listen \
  --agentA personas/jamie.md \
  --agentB personas/riley.md \
  --visual-pause 6.0
```

**How it works:**
1. Every `rounds_per_topic` rounds (set in iceBreakers.md), next topic is added to queue
2. Every `--listen-interval` turns, room checks queue and whispers the next topic
3. Topic is reinforced for `--topic-hold-turns` turns before moving to the next
4. When the list ends, it cycles back to the beginning
5. Topics from ambient listening and icebreakers share the same queue

**Timing parameters explained:**
- `rounds_per_topic` (in iceBreakers.md): How often to add a new icebreaker to the queue
- `--listen-interval`: How often the room checks the queue and whispers a topic
- `--topic-hold-turns`: How many turns to keep reinforcing each topic before moving on

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
├── listener.py       # Ambient listening module (mic + Whisper)
├── personaGen.py     # Interactive persona builder
├── iceBreakers.md    # Structured topic rotation list (optional)
├── Artboard 1.png    # Default visual mode image (comic speech balloons)
├── personas/         # Persona markdown files
│   ├── agent_a.md    # Skeptical physicist (Dr. Lena Hart)
│   ├── agent_b.md    # Mystic panpsychist (Mira Sol)
│   ├── jamie.md      # Pragmatic optimist (casual)
│   ├── riley.md      # Skeptical romantic (casual)
│   ├── room.md       # The whispering room (ambient listening)
│   ├── judge.md      # Neutral referee
│   └── ...
├── logs/             # Conversation transcripts (auto-generated)
├── requirements.txt  # Python dependencies
└── README.md
```

---

## License

MIT License. See LICENSE for details.
