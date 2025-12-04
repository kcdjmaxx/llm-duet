# LLM DuetLLM Duet is a small framework for running multi-agent conversations between local LLMs using Ollama.

It’s designed for:
	•	Running two+ personas against each other (e.g. skeptical physicist vs mystic panpsychist)
	•	Swapping personas and models via CLI flags
	•	Optional judge/referee and user persona that interject periodically
	•	Saving the full discussion as a markdown log

Everything runs locally on your machine using Ollama’s HTTP API.

⸻

Features
	•	Persona system via markdown files with Name / ShortName headers
	•	Per-agent models (Agent A and B may use same or different models)
	•	Optional judge agent that critiques the dialogue
	•	Optional user persona (e.g. Max / DJ Maxx) that jumps in periodically
	•	Markdown logging of the full conversation
	•	CLI flags for personas, models, intervals, max turns, log file name, color, and more

⸻

Requirements
	•	macOS or Linux
	•	Ollama installed
	•	Python 3.10+
	•	requests Python library

Install the Python dependencies using:

pip install -r requirements.txt

Make sure you have an Ollama model installed, for example:

ollama pull mistral

⸻

Installation

Clone the repo:

git clone https://github.com/kcdjmaxx/llm-duet.git
cd llm-duet

Create and activate the virtual environment:

python -m venv .venv
source .venv/bin/activate

⸻

Persona Files

Personas live in personas/ as Markdown files.
Each must begin with:

Name: Full Display Name
ShortName: ShortTag

Example:

Name: Dr. Lena Hart
ShortName: Hart

You can add any long-form system instructions below that.

⸻

Usage

To run the conversation:

python duet.py

You will be prompted for a topic:

Enter start topic:

Then the agents will talk autonomously.
Stop anytime with Ctrl-C.

Logs are saved in:

logs/

⸻

CLI Flags

List all options:

python duet.py –help

Key flags:

-A, –agentA – persona file for Agent A
-B, –agentB – persona file for Agent B
-m, –model – default model for both agents
-MA, –modelA – model override for Agent A
-MB, –modelB – model override for Agent B
–judge-persona – judge/referee persona
–judge-model – model for judge
–judge-interval – how often judge comments
–user-persona – persona representing YOU
–user-interval – how often user persona interjects
–max-turns – stop after N turns
–logfile – custom log path
–no-color – disable terminal colors

⸻

Examples

Default:

python duet.py

Use Mistral:

python duet.py -m mistral

Different models for each agent:

python duet.py -MA mistral -MB qwen2.5:7b

Add a judge:

python duet.py 
–judge-persona personas/judge.md 
–judge-interval 4

Add your persona every 3 turns:

python duet.py 
–user-persona personas/agent_user.md 
–user-interval 3

Limit to 10 turns:

python duet.py –max-turns 10

Disable color:

python duet.py –no-color

⸻

License

MIT License. See LICENSE for details.
