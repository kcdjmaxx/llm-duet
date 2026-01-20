#!/usr/bin/env python3
import os
import textwrap

def ask(question):
    print("\n" + question)
    return input("> ").strip()

def multiline_input(prompt):
    print(f"\n{prompt}")
    print("Enter text below. Finish with a single line containing only 'END'.\n")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)

def generate_persona(answers):
    name = answers["name"]
    shortname = answers["shortname"]
    worldview = answers["worldview"]
    personality = answers["personality"]
    communication = answers["communication"]
    gears = answers["gears"]
    role = answers["role"]
    domains = answers["domains"]
    quirks = answers["quirks"]
    mission = answers["mission"]

    md = f"""Name: {name}
ShortName: {shortname}

# Persona Overview
{worldview}

## Core Traits
{personality}

## Expressive Gears
{gears}

## Behavioral Dynamics
They respond to disagreements, confusion, emotional tone shifts, logic, symbolism, and humor based on their stated worldview and gears. Their interaction profile:
- Negotiates conflict according to their role: **{role}**
- Adapts tone using communication style: **{communication}**
- Handles these domains especially well: {domains}

## Signature Quirks
{quirks}

## Mission
{mission}
"""
    return md


def main():
    print("\n====================================")
    print("      Persona Generator (CLI)       ")
    print("  Creates personas in Markdown      ")
    print("====================================\n")

    # --- STEP 1: Ask Clarifying Questions ---
    answers = {}

    answers["name"] = ask("1. What is the persona’s full name? (Or type 'generate' for an invented one)")
    if answers["name"].lower() == "generate":
        answers["name"] = ask("Enter the name you want me to use, or leave blank to auto-generate:") or "Unnamed Persona"

    answers["shortname"] = ask("2. What short name/tag should they use in conversation? (e.g. 'Vex', 'Solari')")

    answers["worldview"] = multiline_input(
        "3. Describe their worldview, goals, backstory, and tone.\n"
        "Give me 3–6 sentences. Type 'END' when finished."
    )

    answers["personality"] = multiline_input(
        "4. List core traits (bullet points allowed). Type 'END' when finished."
    )

    answers["communication"] = ask(
        "5. What communication style do they have? (e.g. calm, sarcastic, poetic, chaotic)"
    )

    answers["gears"] = multiline_input(
        "6. Describe their expressive gears (e.g. Rational, Passionate, Surreal, Unhinged).\n"
        "Write each gear as a Markdown section. Type 'END' when finished."
    )

    answers["role"] = ask(
        "7. What is their role in multi-agent conversations? (partner, rival, antagonist, chaos catalyst, etc.)"
    )

    answers["domains"] = ask(
        "8. What domains are they comfortable discussing? (comma separated list)"
    )

    answers["quirks"] = multiline_input(
        "9. List 3–6 signature quirks. Bullet points encouraged. Type 'END' when finished."
    )

    answers["mission"] = multiline_input(
        "10. What is this persona’s mission or purpose in conversations?\n"
        "Type 'END' when finished."
    )

    # --- STEP 2: Generate Persona Markdown File ---
    persona_md = generate_persona(answers)

    # Ensure personas directory exists
    os.makedirs("personas", exist_ok=True)

    # File naming
    safe_name = answers["shortname"].replace(" ", "_").lower()
    filename = f"personas/{safe_name}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(persona_md)

    print("\n====================================")
    print(" Persona file generated successfully!")
    print("====================================")
    print(f"\nSaved to:\n  {filename}\n")
    print("Preview:\n")
    print(persona_md)


if __name__ == "__main__":
    main()
