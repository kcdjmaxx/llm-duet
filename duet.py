import argparse
import os
import time
from datetime import datetime

import requests


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a two-agent LLM duet with optional judge and user interjections.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-A",
        "--agentA",
        default="personas/agent_a.md",
        help="Path to persona file for Agent A (e.g. skeptical physicist).",
    )

    parser.add_argument(
        "-B",
        "--agentB",
        default="personas/agent_b.md",
        help="Path to persona file for Agent B (e.g. mystic panpsychist).",
    )

    # Base/shared model
    parser.add_argument(
        "-m",
        "--model",
        default="mistral",
        help="Default model to use for BOTH agents unless overridden (Ollama tag, e.g. 'mistral' or 'mistral:7b').",
    )

    # Per-agent model overrides
    parser.add_argument(
        "-MA",
        "--modelA",
        help="Optional: specific model for Agent A (overrides --model).",
    )

    parser.add_argument(
        "-MB",
        "--modelB",
        help="Optional: specific model for Agent B (overrides --model).",
    )

    # Judge / referee
    parser.add_argument(
        "--judge-persona",
        help="Optional persona file for a third 'judge' / referee agent.",
    )

    parser.add_argument(
        "--judge-model",
        help="Optional model for judge agent (defaults to base --model).",
    )

    parser.add_argument(
        "--judge-interval",
        type=int,
        default=0,
        help="Every N turns, the judge comments on the last exchange (0 disables judge).",
    )

    # User persona (you)
    parser.add_argument(
        "--user-persona",
        help="Optional persona file representing YOU as a third voice.",
    )

    parser.add_argument(
        "--user-interval",
        type=int,
        default=0,
        help="Every N turns, the user persona interjects (0 disables).",
    )

    # Other behavior
    parser.add_argument(
        "--max-turns",
        type=int,
        default=0,
        help="Maximum number of A↔B turns (0 = infinite until Ctrl-C).",
    )

    parser.add_argument(
        "--logfile",
        help="Optional explicit log file path. If omitted, a timestamped .md file in logs/ is used.",
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored terminal output.",
    )

    return parser.parse_args()


# Colors / formatting helpers
class Colors:
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def cwrap(text, color, use_color=True):
    if not use_color:
        return text
    return f"{color}{text}{Colors.RESET}"


def load_persona(path):
    """
    Load persona markdown and extract:
      - Name: Full display name
      - ShortName: Short label used in terminal
      - text: full markdown content
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    name = None
    short_name = None

    for line in text.splitlines():
        lower = line.lower()
        if lower.startswith("name:"):
            name = line.split(":", 1)[1].strip()
        elif lower.startswith("shortname:"):
            short_name = line.split(":", 1)[1].strip()
        if name and short_name:
            break

    if not name:
        name = os.path.splitext(os.path.basename(path))[0]
    if not short_name:
        short_name = name

    return {
        "name": name,
        "short_name": short_name,
        "text": text,
    }


def chat_with_model(ollama_url, model_name, messages):
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "options": {
            "num_ctx": 4096,
            "temperature": 0.7,
        },
    }
    resp = requests.post(ollama_url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]


def create_log_file(topic, explicit_path=None):
    if explicit_path:
        # If explicit path has a directory component, ensure it exists
        directory = os.path.dirname(explicit_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        path = explicit_path
    else:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_topic = "".join(
            c for c in topic[:40] if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_topic = safe_topic.replace(" ", "_") or "conversation"
        os.makedirs("logs", exist_ok=True)
        path = f"logs/{ts}_{safe_topic}.md"

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# LLM Duet Conversation\n\n")
        f.write(f"- **Start time:** {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"- **Topic:** {topic}\n\n")
        f.write("---\n\n")
    return path


def append_log(log_path, speaker_name, text):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"### {speaker_name}\n\n")
        for line in text.splitlines():
            f.write(f"> {line}\n")
        f.write("\n\n")


def main():
    args = parse_args()

    # Ollama base URL
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")

    # Figure out models
    model_a = args.modelA or args.model
    model_b = args.modelB or args.model
    model_judge = args.judge_model or args.model
    model_user = args.model  # could be separated later

    use_color = not args.no_color

    topic = input("Enter start topic (word or full prompt): ").strip()
    if not topic:
        print("No topic entered, exiting.")
        return

    # Load core personas
    persona_a = load_persona(args.agentA)
    persona_b = load_persona(args.agentB)

    name_a = persona_a["name"]
    short_a = persona_a["short_name"]
    text_a = persona_a["text"]

    name_b = persona_b["name"]
    short_b = persona_b["short_name"]
    text_b = persona_b["text"]

    # Optional judge persona
    judge_persona = None
    if args.judge_persona:
        judge_persona = load_persona(args.judge_persona)

    # Optional user persona
    user_persona = None
    if args.user_persona:
        user_persona = load_persona(args.user_persona)

    # Create log
    log_path = create_log_file(topic, args.logfile)
    print(f"Logging conversation to: {log_path}")
    line = f"Participants: {name_a} ({short_a}), {name_b} ({short_b})"
    if judge_persona:
        line += f", Judge: {judge_persona['name']} ({judge_persona['short_name']})"
    if user_persona:
        line += f", User persona: {user_persona['name']} ({user_persona['short_name']})"
    print(line + "\n")

    # System messages
    system_a = {
        "role": "system",
        "content": (
            text_a
            + "\n\n"
            + f"The other participant in this conversation is {name_b}. "
            "You are having a back-and-forth dialogue with them.\n\n"
            "The human provided this starting topic. Use it as the thread for the dialogue:\n"
            + topic
        ),
    }
    system_b = {
        "role": "system",
        "content": (
            text_b
            + "\n\n"
            + f"The other participant in this conversation is {name_a}. "
            "You are having a back-and-forth dialogue with them.\n\n"
            "The human provided this starting topic. Use it as the thread for the dialogue:\n"
            + topic
        ),
    }

    conversation_a = [system_a]
    conversation_b = [system_b]

    # Judge conversation (if any)
    conversation_j = None
    if judge_persona:
        conversation_j = [
            {
                "role": "system",
                "content": judge_persona["text"]
                + "\n\nYou are a neutral judge/referee analyzing the dialogue "
                f"between {name_a} and {name_b}. You comment only when asked, "
                "and you focus on clarity, rigor, and synthesis.",
            }
        ]

    # User persona conversation (if any)
    conversation_u = None
    if user_persona:
        conversation_u = [
            {
                "role": "system",
                "content": user_persona["text"]
                + "\n\nYou are a third voice occasionally stepping into the dialogue. "
                "You represent the human who started the topic, asking sharp questions, "
                "connecting ideas, or redirecting when helpful.",
            }
        ]

    print("--- Conversation started (Ctrl-C to stop) ---\n")

    turn = 0  # A↔B exchange counter

    try:
        # First move: A starts
        conversation_a.append(
            {
                "role": "user",
                "content": (
                    "The human has just given the topic above. "
                    f"Start the conversation by making the first move and inviting {name_b} to respond."
                ),
            }
        )
        a_reply = chat_with_model(ollama_url, model_a, conversation_a)
        print(cwrap(f"[{short_a}]:", Colors.BLUE, use_color), a_reply, "\n")
        append_log(log_path, name_a, a_reply)

        # Main loop
        while True:
            turn += 1

            # B responds to A
            conversation_b.append({"role": "user", "content": a_reply})
            b_reply = chat_with_model(ollama_url, model_b, conversation_b)
            print(cwrap(f"[{short_b}]:", Colors.MAGENTA, use_color), b_reply, "\n")
            append_log(log_path, name_b, b_reply)

            # A responds to B
            conversation_a.append({"role": "user", "content": b_reply})
            a_reply = chat_with_model(ollama_url, model_a, conversation_a)
            print(cwrap(f"[{short_a}]:", Colors.BLUE, use_color), a_reply, "\n")
            append_log(log_path, name_a, a_reply)

            # Judge interjection
            if (
                judge_persona
                and args.judge_interval > 0
                and turn % args.judge_interval == 0
            ):
                prompt = (
                    f"{name_a} just said:\n{a_reply}\n\n"
                    f"{name_b} just said:\n{b_reply}\n\n"
                    "As the judge, briefly evaluate the last exchange. "
                    "Highlight any strong points, weak points, misconceptions, "
                    "and suggest how the dialogue could go deeper or clearer next."
                )
                conversation_j.append({"role": "user", "content": prompt})
                j_reply = chat_with_model(ollama_url, model_judge, conversation_j)
                print(
                    cwrap(
                        f"[{judge_persona['short_name']}]:",
                        Colors.GREEN,
                        use_color,
                    ),
                    j_reply,
                    "\n",
                )
                append_log(log_path, judge_persona["name"], j_reply)

            # User persona interjection
            if (
                user_persona
                and args.user_interval > 0
                and turn % args.user_interval == 0
            ):
                prompt = (
                    f"{name_a} just said:\n{a_reply}\n\n"
                    f"{name_b} just said:\n{b_reply}\n\n"
                    "As the user persona, step into the conversation with a short comment or question "
                    "that pushes both agents toward more insight, rigor, or practicality. "
                    "You are allowed to disagree, redirect, or connect to a bigger picture."
                )
                conversation_u.append({"role": "user", "content": prompt})
                u_reply = chat_with_model(ollama_url, model_user, conversation_u)
                print(
                    cwrap(
                        f"[{user_persona['short_name']}]:",
                        Colors.CYAN,
                        use_color,
                    ),
                    u_reply,
                    "\n",
                )
                append_log(log_path, user_persona["name"], u_reply)

            # Stop if max_turns reached
            if args.max_turns > 0 and turn >= args.max_turns:
                print("\nMax turns reached, stopping conversation.")
                break

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n\nStopping conversation (Ctrl-C).")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write("---\n\nConversation stopped.\n")
    print(f"Final log saved to: {log_path}")


if __name__ == "__main__":
    main()
