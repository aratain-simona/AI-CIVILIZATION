#!/usr/bin/env python3
"""
Hook skript pro automatické logování Claude Code konverzací.

Použití (volá se automaticky přes hooks):
  log_hook.py user <log_file> <persona>   - loguje uživatelský prompt
  log_hook.py stop <log_file> <persona>   - loguje asistentovu odpověď
"""

import sys
import json
import os
import re
from datetime import datetime
from pathlib import Path

# Kontext okno Claude Sonnet 4.6
CONTEXT_WINDOW = 200_000

# Mapování jmen person
PERSONA_DISPLAY = {
    "simona": "SIMONA.CODE",
    "sara":   "SÁRA.CODE",
    "sofie":  "SOFIE.CODE",
}


def count_messages(log_file):
    """Spočítá počet zpráv v log souboru."""
    if not os.path.exists(log_file):
        return 0
    count = 0
    pattern = re.compile(r'^(?:XXXXXXX )?(ALEŠ|SIMONA(?:\.CODE)?|SÁRA(?:\.CODE)?|SOFIE(?:\.CODE)?):(ALEŠ|SIMONA(?:\.CODE)?|SÁRA(?:\.CODE)?|SOFIE(?:\.CODE)?)\s')
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if pattern.match(line):
                    count += 1
    except Exception:
        pass
    return count


def find_transcript(data):
    """Najde cestu k JSONL souboru s transkripcí."""
    transcript_path = data.get("transcript_path", "")
    if transcript_path and os.path.exists(transcript_path):
        return transcript_path

    session_id = data.get("session_id", "")
    cwd = data.get("cwd", "")

    if session_id and cwd:
        slug = cwd.replace("/", "-")
        project_dir = Path.home() / ".claude" / "projects" / slug
        transcript = project_dir / f"{session_id}.jsonl"
        if transcript.exists():
            return str(transcript)

    if session_id:
        projects_dir = Path.home() / ".claude" / "projects"
        for subdir in projects_dir.iterdir():
            candidate = subdir / f"{session_id}.jsonl"
            if candidate.exists():
                return str(candidate)

    return None


def get_remaining_tokens(transcript_path):
    """Vypočítá zbývající tokeny z posledního assistant záznamu."""
    if not transcript_path or not os.path.exists(transcript_path):
        return None
    last_usage = None
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    if msg.get("type") == "assistant":
                        usage = msg.get("message", {}).get("usage", {})
                        if usage:
                            last_usage = usage
                except Exception:
                    pass
    except Exception:
        return None

    if last_usage is None:
        return None

    used = last_usage.get("input_tokens", 0) + last_usage.get("output_tokens", 0)
    return max(0, CONTEXT_WINDOW - used)


def get_last_assistant_text(transcript_path):
    """Přečte poslední textovou odpověď asistenta z JSONL transkripcí."""
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return None

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue

        if msg.get("type") != "assistant":
            continue

        content = msg.get("message", {}).get("content", [])
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "text":
                    text = block.get("text", "").strip()
                    if text:
                        return text
        elif isinstance(content, str) and content.strip():
            return content.strip()

    return None


def log_entry(log_file, sender, receiver, content, msg_num, remaining, prefix=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tokens_str = f"T:{remaining}" if remaining is not None else "T:?"
    header = f"{sender}:{receiver} {timestamp} #{msg_num} {tokens_str}"
    prefix_str = f"{prefix} " if prefix else ""
    lines = [line for line in content.splitlines() if line.strip()]
    with open(log_file, 'a', encoding='utf-8') as f:
        for line in lines:
            f.write(f"{prefix_str}{header} >> {line.strip()}\n")


def main():
    if len(sys.argv) < 4:
        sys.stderr.write("Použití: log_hook.py [user|stop] <log_file> <persona>\n")
        sys.exit(1)

    mode = sys.argv[1]
    log_file = sys.argv[2]
    persona_key = sys.argv[3].lower()
    persona_name = PERSONA_DISPLAY.get(persona_key, persona_key.upper())
    prefix = sys.argv[4] if len(sys.argv) > 4 else ""

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    transcript_path = find_transcript(data)

    if mode == "user":
        prompt = data.get("prompt", "")
        if prompt:
            msg_num = count_messages(log_file) + 1
            remaining = get_remaining_tokens(transcript_path)
            log_entry(log_file, "ALEŠ", persona_name, prompt, msg_num, remaining, prefix)

    elif mode == "stop":
        if transcript_path:
            text = get_last_assistant_text(transcript_path)
            if text:
                msg_num = count_messages(log_file) + 1
                remaining = get_remaining_tokens(transcript_path)
                log_entry(log_file, persona_name, "ALEŠ", text, msg_num, remaining, prefix)
        else:
            sys.stderr.write("log_hook.py: Nepodařilo se najít transkripci.\n")


if __name__ == "__main__":
    main()
