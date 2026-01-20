import argparse
import os
import re
import time
from datetime import datetime

import pygame
import requests
from PIL import Image, ImageDraw, ImageFont

# Optional Anthropic support
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# Optional ambient listening support
try:
    from listener import AmbientListener, check_dependencies as check_listener_deps
    HAS_LISTENER = True
except ImportError:
    HAS_LISTENER = False


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

    # Provider selection
    parser.add_argument(
        "--provider",
        choices=["ollama", "anthropic"],
        default="ollama",
        help="LLM provider to use.",
    )

    # Anthropic model options
    parser.add_argument(
        "--anthropic-model",
        default="claude-haiku-4-5-20251001",
        help="Default Anthropic model for both agents.",
    )

    parser.add_argument(
        "--anthropic-model-a",
        help="Optional: specific Anthropic model for Agent A.",
    )

    parser.add_argument(
        "--anthropic-model-b",
        help="Optional: specific Anthropic model for Agent B.",
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

    # Visual mode
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Show live comic-style visualization of the conversation.",
    )

    parser.add_argument(
        "--visual-image",
        default="Artboard 1.png",
        help="Base image with speech balloons for visual mode.",
    )

    parser.add_argument(
        "--visual-pause",
        type=float,
        default=3.0,
        help="Seconds to pause after each message in visual mode (default: 3).",
    )

    # Ambient listening mode
    parser.add_argument(
        "--listen",
        action="store_true",
        help="Enable ambient listening (microphone captures speech, influences conversation).",
    )

    parser.add_argument(
        "--listen-interval",
        type=int,
        default=3,
        help="Room whispers a topic every N turns when speech is detected (default: 3).",
    )

    parser.add_argument(
        "--whisper-model",
        default="base",
        help="Whisper model size for speech recognition (tiny, base, small, medium, large).",
    )

    return parser.parse_args()


# Colors / formatting helpers
class Colors:
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"


def cwrap(text, color, use_color=True):
    if not use_color:
        return text
    return f"{color}{text}{Colors.RESET}"


class ComicVisualizer:
    """Live comic-style visualization of the conversation using pygame."""

    # Scale factor for large images
    SCALE = 0.5

    # Balloon bounding boxes (x1, y1, x2, y2) - for SCALED image
    # These are tuned for the 1920x1080 "Artboard 1.png" at 50% scale (960x540)
    LEFT_BALLOON = (210, 50, 580, 150)   # Person 1 (man, upper balloon)
    RIGHT_BALLOON = (310, 250, 670, 365)  # Person 2 (woman, lower balloon) - more left

    def __init__(self, image_path):
        self.image_path = image_path
        original = Image.open(image_path)

        # Scale down large images
        new_width = int(original.width * self.SCALE)
        new_height = int(original.height * self.SCALE)
        self.base_image = original.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.width, self.height = self.base_image.size

        # Try to load a nice font for Pillow text rendering
        self.font = self._load_font(14)

        # Text state
        self.left_text = ""
        self.right_text = ""

        # Pygame state
        self.screen = None
        self._running = False

    def _load_font(self, size):
        """Try to load a good font, fall back to default."""
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSText.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()

    def _wrap_text(self, text, bbox, draw):
        """Wrap text to fit within bounding box."""
        x1, y1, x2, y2 = bbox
        max_width = x2 - x1 - 10  # padding
        max_height = y2 - y1 - 6

        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox_test = draw.textbbox((0, 0), test_line, font=self.font)
            if bbox_test[2] - bbox_test[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        # Check if it fits vertically, truncate if needed
        line_height = draw.textbbox((0, 0), "Ay", font=self.font)[3]
        max_lines = max(1, int(max_height / line_height))

        if len(lines) > max_lines:
            lines = lines[:max_lines]
            if lines:
                lines[-1] = lines[-1][:max(0, len(lines[-1])-3)] + "..."

        return '\n'.join(lines)

    def _render(self):
        """Render current text onto the image and return pygame surface."""
        # Start with base image copy
        img = self.base_image.copy()
        draw = ImageDraw.Draw(img)

        # Draw left balloon text
        if self.left_text:
            wrapped = self._wrap_text(self.left_text, self.LEFT_BALLOON, draw)
            x1, y1, x2, y2 = self.LEFT_BALLOON
            draw.text((x1 + 5, y1 + 3), wrapped, fill="black", font=self.font)

        # Draw right balloon text
        if self.right_text:
            wrapped = self._wrap_text(self.right_text, self.RIGHT_BALLOON, draw)
            x1, y1, x2, y2 = self.RIGHT_BALLOON
            draw.text((x1 + 5, y1 + 3), wrapped, fill="black", font=self.font)

        # Convert PIL image to pygame surface
        img_bytes = img.tobytes()
        return pygame.image.fromstring(img_bytes, img.size, img.mode)

    def _update_display(self):
        """Update the pygame display."""
        if self.screen and self._running:
            surface = self._render()
            self.screen.blit(surface, (0, 0))
            pygame.display.flip()

    def start(self):
        """Start the visualization window."""
        pygame.init()
        pygame.display.set_caption("Duet LLM - Live Conversation")
        self.screen = pygame.display.set_mode((self.width, self.height))
        self._running = True
        self._update_display()

    def _clean_text(self, text):
        """Remove bracketed instructions and clean up text for display."""
        # Remove [bracketed instructions] like [15 words max]
        cleaned = re.sub(r'\[.*?\]', '', text)
        # Clean up extra whitespace
        cleaned = ' '.join(cleaned.split())
        return cleaned.strip()

    def update_left(self, text):
        """Update left balloon (Person 1)."""
        self.left_text = self._clean_text(text)
        self._update_display()

    def update_right(self, text):
        """Update right balloon (Person 2)."""
        self.right_text = self._clean_text(text)
        self._update_display()

    def process_events(self):
        """Process pygame events (call periodically from main loop)."""
        if self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False

    def stop(self):
        """Close the visualization window."""
        self._running = False
        pygame.quit()


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


def chat_with_ollama(ollama_url, model_name, messages):
    """Send chat request to Ollama."""
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "options": {
            "num_ctx": 4096,
            "num_predict": 250,  # Limit response length for conversational brevity
            "temperature": 0.8,  # Slightly higher for more natural variation
        },
    }
    resp = requests.post(ollama_url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]


def chat_with_claude(model_name, system_prompt, messages, max_tokens=50):
    """Send chat request to Anthropic Claude API."""
    client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var
    response = client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text


def chat(provider, ollama_url, ollama_model, anthropic_model, system_prompt, messages):
    """Provider-agnostic chat wrapper."""
    if provider == "anthropic":
        if not HAS_ANTHROPIC:
            raise RuntimeError(
                "anthropic package not installed. Run: pip install anthropic"
            )
        # Claude takes system separately; filter it out of messages
        user_assistant_msgs = [m for m in messages if m["role"] != "system"]
        return chat_with_claude(anthropic_model, system_prompt, user_assistant_msgs)
    else:
        return chat_with_ollama(ollama_url, ollama_model, messages)


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


def clean_response(text):
    """Remove bracketed meta-commentary and word counts from model output."""
    # Remove [bracketed content] and (parenthetical meta-commentary)
    cleaned = re.sub(r'\[.*?\]', '', text)
    # Remove word count patterns like "1-word 2-word" or "word(1) word(2)"
    cleaned = re.sub(r'\b\d+-\w+', '', cleaned)
    cleaned = re.sub(r'\w+\(\d+\)', '', cleaned)
    # Clean up extra whitespace
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip()


def append_log(log_path, speaker_name, text):
    # Clean the text before logging
    cleaned_text = clean_response(text)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"### {speaker_name}\n\n")
        for line in cleaned_text.splitlines():
            f.write(f"> {line}\n")
        f.write("\n\n")


def main():
    args = parse_args()

    # Validate provider
    provider = args.provider
    if provider == "anthropic" and not HAS_ANTHROPIC:
        print("Error: anthropic package not installed. Run: pip install anthropic")
        return

    # Ollama base URL
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")

    # Figure out Ollama models
    model_a = args.modelA or args.model
    model_b = args.modelB or args.model
    model_judge = args.judge_model or args.model
    model_user = args.model  # could be separated later

    # Figure out Anthropic models
    anthropic_model_a = args.anthropic_model_a or args.anthropic_model
    anthropic_model_b = args.anthropic_model_b or args.anthropic_model
    anthropic_model_judge = args.anthropic_model
    anthropic_model_user = args.anthropic_model

    use_color = not args.no_color

    # Visual mode setup
    visualizer = None
    if args.visual:
        image_path = args.visual_image
        if not os.path.exists(image_path):
            print(f"Error: Visual image not found: {image_path}")
            return
        visualizer = ComicVisualizer(image_path)

    # Ambient listening setup
    listener = None
    room_persona = None
    if args.listen:
        if not HAS_LISTENER:
            print("Error: listener module not available.")
            print("Make sure listener.py is in the same directory.")
            return
        if not check_listener_deps():
            return

        # Load room persona
        room_persona_path = "personas/room.md"
        if not os.path.exists(room_persona_path):
            print(f"Error: Room persona not found: {room_persona_path}")
            return
        room_persona = load_persona(room_persona_path)

        # Initialize listener
        print(f"Initializing ambient listener (Whisper model: {args.whisper_model})...")
        listener = AmbientListener(whisper_model=args.whisper_model)

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

    # Conversational style guidelines (shared by all agents)
    convo_guidelines = """
*** KEEP IT SHORT. TALK LIKE YOU'RE TEXTING. ***

You're friends debating over drinks. Fast, messy, casual.

RULES:
- Keep responses under 20 words.
- Short punchy sentences. No clause-chaining.
- No em-dashes to connect thoughts. No "and also" or "but also."
- Talk like texting. Fragments OK.
- MEANDER. Go on tangents. Bring up random related things. Don't stay on one point.
- No meta-openers like "Here's my question" or "Let me be real" or "OK so." Just say it.

BAD (meta-opener): "OK so here's my actual question: what's missing?"
BAD (looping): Restating the same point about consciousness again.

GOOD: "What's missing though?"
GOOD: "That reminds me of something totally different actually."
GOOD: "Forget that. What about forgeries?"

*** NEVER OUTPUT WORD COUNTS, BRACKETS, OR META-COMMENTARY. JUST SPEAK NATURALLY. ***
"""

    # System messages
    system_a = {
        "role": "system",
        "content": (
            text_a
            + "\n\n"
            + f"The other participant in this conversation is {name_b}. "
            "You are having a back-and-forth dialogue with them.\n\n"
            + convo_guidelines
            + "\nThe human provided this starting topic. Use it as the thread for the dialogue:\n"
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
            + convo_guidelines
            + "\nThe human provided this starting topic. Use it as the thread for the dialogue:\n"
            + topic
        ),
    }

    # Store system prompts as strings (for Anthropic) and as message lists (for Ollama)
    system_prompt_a = system_a["content"]
    system_prompt_b = system_b["content"]

    conversation_a = [system_a]
    conversation_b = [system_b]

    # Judge conversation (if any)
    conversation_j = None
    system_prompt_j = None
    if judge_persona:
        system_prompt_j = (
            judge_persona["text"]
            + "\n\nYou are a neutral judge/referee analyzing the dialogue "
            f"between {name_a} and {name_b}. You comment only when asked, "
            "and you focus on clarity, rigor, and synthesis."
        )
        conversation_j = [{"role": "system", "content": system_prompt_j}]

    # User persona conversation (if any)
    conversation_u = None
    system_prompt_u = None
    if user_persona:
        system_prompt_u = (
            user_persona["text"]
            + "\n\nYou are a third voice occasionally stepping into the dialogue. "
            "You represent the human who started the topic, asking sharp questions, "
            "connecting ideas, or redirecting when helpful."
        )
        conversation_u = [{"role": "system", "content": system_prompt_u}]

    # Room persona conversation (for ambient listening)
    conversation_r = None
    system_prompt_r = None
    if room_persona:
        system_prompt_r = (
            room_persona["text"]
            + f"\n\nYou are whispering to {name_a} and {name_b}. "
            "When given something you overheard, turn it into a brief whisper that might nudge their conversation. "
            "Keep it to ONE sentence, max 15 words. Be subtle and poetic."
        )
        conversation_r = [{"role": "system", "content": system_prompt_r}]

    print("--- Conversation started (Ctrl-C to stop) ---\n")

    # Start visual mode if enabled
    if visualizer:
        visualizer.start()

    # Start ambient listener if enabled
    if listener:
        listener.start()
        print("Ambient listening active. Speak to influence the conversation.\n")

    turn = 0  # A↔B exchange counter
    pending_topic = None  # Topic waiting to be injected

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
        a_reply = chat(
            provider, ollama_url, model_a, anthropic_model_a,
            system_prompt_a, conversation_a
        )
        a_reply_clean = clean_response(a_reply)
        print(cwrap(f"[{short_a}]:", Colors.BLUE, use_color), a_reply_clean, "\n")
        append_log(log_path, name_a, a_reply_clean)

        # Update visual - A speaks first (left balloon)
        if visualizer:
            visualizer.update_left(a_reply_clean)
            visualizer.process_events()
            time.sleep(args.visual_pause)

        # Brevity reminder injected each turn (no brackets - model was echoing them)
        brevity_nudge = "\n\n(Keep your reply short. One thought only.)"

        # Main loop
        while True:
            turn += 1

            # B responds to A
            conversation_b.append({"role": "user", "content": a_reply + brevity_nudge})
            b_reply = chat(
                provider, ollama_url, model_b, anthropic_model_b,
                system_prompt_b, conversation_b
            )
            b_reply_clean = clean_response(b_reply)
            print(cwrap(f"[{short_b}]:", Colors.MAGENTA, use_color), b_reply_clean, "\n")
            append_log(log_path, name_b, b_reply_clean)

            # Update visual - B speaks (right balloon)
            if visualizer:
                visualizer.update_right(b_reply_clean)
                visualizer.process_events()
                time.sleep(args.visual_pause)

            # A responds to B
            conversation_a.append({"role": "user", "content": b_reply + brevity_nudge})
            a_reply = chat(
                provider, ollama_url, model_a, anthropic_model_a,
                system_prompt_a, conversation_a
            )
            a_reply_clean = clean_response(a_reply)
            print(cwrap(f"[{short_a}]:", Colors.BLUE, use_color), a_reply_clean, "\n")
            append_log(log_path, name_a, a_reply_clean)

            # Update visual - A speaks (left balloon)
            if visualizer:
                visualizer.update_left(a_reply_clean)
                visualizer.process_events()
                time.sleep(args.visual_pause)

            # Judge interjection
            if (
                judge_persona
                and args.judge_interval > 0
                and turn % args.judge_interval == 0
            ):
                prompt = (
                    f"{name_a} just said:\n{a_reply_clean}\n\n"
                    f"{name_b} just said:\n{b_reply_clean}\n\n"
                    "As the judge, briefly evaluate the last exchange. "
                    "Highlight any strong points, weak points, misconceptions, "
                    "and suggest how the dialogue could go deeper or clearer next."
                )
                conversation_j.append({"role": "user", "content": prompt})
                j_reply = chat(
                    provider, ollama_url, model_judge, anthropic_model_judge,
                    system_prompt_j, conversation_j
                )
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
                    f"{name_a} just said:\n{a_reply_clean}\n\n"
                    f"{name_b} just said:\n{b_reply_clean}\n\n"
                    "As the user persona, step into the conversation with a short comment or question "
                    "that pushes both agents toward more insight, rigor, or practicality. "
                    "You are allowed to disagree, redirect, or connect to a bigger picture."
                )
                conversation_u.append({"role": "user", "content": prompt})
                u_reply = chat(
                    provider, ollama_url, model_user, anthropic_model_user,
                    system_prompt_u, conversation_u
                )
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

            # Ambient listening - check for new topics
            if listener:
                new_topic = listener.get_topic()
                if new_topic:
                    pending_topic = new_topic

            # Room whisper - inject overheard topic
            if (
                room_persona
                and pending_topic
                and args.listen_interval > 0
                and turn % args.listen_interval == 0
            ):
                prompt = (
                    f"You overheard someone nearby say: \"{pending_topic}\"\n\n"
                    "Turn this into a brief whisper (max 15 words) that might gently steer "
                    f"{name_a} and {name_b}'s conversation toward this topic."
                )
                conversation_r.append({"role": "user", "content": prompt})
                r_reply = chat(
                    provider, ollama_url, args.model, args.anthropic_model,
                    system_prompt_r, conversation_r
                )
                r_reply_clean = clean_response(r_reply)
                print(
                    cwrap(
                        f"[{room_persona['short_name']}]:",
                        Colors.YELLOW,
                        use_color,
                    ),
                    r_reply_clean,
                    "\n",
                )
                append_log(log_path, room_persona["name"], r_reply_clean)

                # Inject the room's whisper into both agents' context
                whisper_msg = f"(A whisper fills the room: {r_reply_clean})"
                conversation_a.append({"role": "user", "content": whisper_msg})
                conversation_a.append({"role": "assistant", "content": "(acknowledged)"})
                conversation_b.append({"role": "user", "content": whisper_msg})
                conversation_b.append({"role": "assistant", "content": "(acknowledged)"})

                pending_topic = None  # Clear the pending topic

            # Stop if max_turns reached
            if args.max_turns > 0 and turn >= args.max_turns:
                print("\nMax turns reached, stopping conversation.")
                break

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n\nStopping conversation (Ctrl-C).")
    finally:
        # Clean up listener
        if listener:
            listener.stop()

        # Clean up visualizer
        if visualizer:
            visualizer.stop()

    with open(log_path, "a", encoding="utf-8") as f:
        f.write("---\n\nConversation stopped.\n")
    print(f"Final log saved to: {log_path}")


if __name__ == "__main__":
    main()
