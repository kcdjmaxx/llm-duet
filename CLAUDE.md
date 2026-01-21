# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Duet LLM is a multi-agent conversation framework that runs LLMs against each other. Supports both local models via Ollama and cloud models via Anthropic API. Two personas debate a topic autonomously with optional judge and user persona interjections. Includes a visual mode for art installations that displays conversations in comic-style speech balloons. Ambient listening mode captures microphone input and uses Whisper to transcribe speech, allowing the conversation to shift based on what visitors say in the room.

## Prerequisites

- Python 3.10+
- For Ollama: Ollama installed and running, at least one model pulled (e.g., `ollama pull mistral`)
- For Anthropic: `ANTHROPIC_API_KEY` environment variable set
- For visual mode: pygame and Pillow (included in requirements.txt)
- For ambient listening: sounddevice, faster-whisper, numpy + microphone permissions

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running Conversations

```bash
# Default (uses personas/agent_a.md and agent_b.md with mistral via Ollama)
python duet.py

# Using Anthropic Claude
python duet.py --provider anthropic

# Visual mode (comic-style display)
python duet.py --provider anthropic --visual

# Casual personas (Jamie & Riley)
python duet.py -A personas/jamie.md -B personas/riley.md --provider anthropic

# Ambient listening (art installation mode)
python duet.py --provider anthropic --visual --listen --agentA personas/jamie.md --agentB personas/riley.md --visual-pause 6.0

# With judge interjecting every 4 turns
python duet.py --judge-persona personas/judge.md --judge-interval 4

# Limit conversation length
python duet.py --max-turns 10
```

See all options: `python duet.py --help`

## Creating Personas

Interactive CLI tool:
```bash
python personaGen.py
```

## Architecture

**duet.py** - Main orchestrator
- Parses CLI args for personas, models, providers, intervals
- Loads persona markdown files and extracts `Name:` / `ShortName:` headers
- Maintains separate conversation histories for each agent (A, B, judge, user, room)
- Provider-agnostic chat wrapper supports Ollama and Anthropic
- Visual mode uses pygame to display comic-style speech balloons
- Ambient listening integrates with listener.py to capture and inject topics
- Logs full conversation to markdown in `logs/`

**listener.py** - Ambient listening module
- Captures audio from microphone using sounddevice
- Voice Activity Detection (VAD) filters silence
- Transcribes speech using faster-whisper (local Whisper)
- Queues topics for injection into conversation

**personaGen.py** - Interactive persona builder
- Prompts for worldview, traits, gears, role, quirks, mission
- Outputs structured markdown to `personas/`

**personas/** - Markdown persona files
- Must start with `Name:` and `ShortName:` headers
- Rest is free-form system prompt content
- Expressive "gears" (Rational/Passionate/Surreal/Unhinged) define behavioral modes

**logs/** - Conversation transcripts (auto-generated)

## Persona File Format

```markdown
Name: Dr. Lena Hart
ShortName: Hart

# Persona Overview
<worldview and tone description>

## Core Traits
- Trait 1
- Trait 2

## Expressive Gears
### 1. Rational Mode
<behavior description>

### 2. Passionate Mode
<behavior description>

## Behavioral Dynamics
<how they respond to disagreements, humor, confusion, etc.>

## Mission
<their goal in conversations>
```

## Environment Variables

- `OLLAMA_URL` - Override Ollama endpoint (default: `http://localhost:11434/api/chat`)
- `ANTHROPIC_API_KEY` - Required for `--provider anthropic`

## Conversation Flow

1. User enters a topic
2. Agent A makes opening statement
3. Loop: B responds to A, A responds to B
4. Optional: Judge/user persona interject at configured intervals
5. Ctrl-C or `--max-turns` stops; log is finalized
