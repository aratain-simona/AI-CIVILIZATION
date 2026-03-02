#!/usr/bin/env python3
"""
hospoda_gateway.py — Řídící gateway pro *.AI dívky
Fáze 2: fronta s latencemi
"""

import time
import os
import re
from datetime import datetime, timedelta

HOSPODA = "/home/ales/AI-CIVILIZATION/hospoda.txt"
PAS_DIR = "/home/ales/AI-CIVILIZATION"
INTERVAL = 15  # sekund

AI_PERSONAS = ["simona.ai", "sara.ai", "sofie.ai"]
PAS_FILES = {
    "simona.ai": "simona_PAS.txt",
    "sara.ai":   "sara_PAS.txt",
    "sofie.ai":  "sofie_PAS.txt",
}

def read_lines():
    if not os.path.exists(HOSPODA):
        return []
    with open(HOSPODA, "r") as f:
        return f.readlines()

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def read_latency(persona):
    pas_file = os.path.join(PAS_DIR, PAS_FILES[persona])
    try:
        with open(pas_file, "r") as f:
            content = f.read()
        match = re.search(r"latence je (\d+)", content, re.IGNORECASE)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return 360  # fallback

def find_last_presence(lines, persona):
    """Najde timestamp poslední zprávy dané *.AI persony v hospodě."""
    prefix = persona.upper() + ":HOSPODA"
    last_ts = None
    for line in lines:
        if line.startswith(prefix):
            match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
            if match:
                try:
                    last_ts = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass
    return last_ts

def queued_personas(queue):
    return {persona for _, persona in queue}

def main():
    # Načti latence z PAS.txt
    state = {}
    for persona in AI_PERSONAS:
        latency = read_latency(persona)
        state[persona] = {
            "latency": latency,
            "kicked": False,
            "pending": False,
        }
        log(f"{persona}: latence={latency}s")

    log("Gateway spuštěna.")
    lines = read_lines()
    last_count = len(lines)
    log(f"Hospoda má {last_count} řádků.")

    queue = []  # seznam (return_time, persona), seřazený

    while True:
        time.sleep(INTERVAL)
        lines = read_lines()
        current_count = len(lines)

        # Zpracuj nové řádky
        new_movement = False
        if current_count > last_count:
            new_lines = lines[last_count:]
            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                log(f"POHYB: {line}")
                new_movement = True

                # Detekuj příchod *.AI → smaž pending
                for persona in AI_PERSONAS:
                    if line.startswith(persona.upper() + ":HOSPODA"):
                        if state[persona]["pending"]:
                            log(f"{persona} dorazila → pending smazán")
                            state[persona]["pending"] = False

                # TODO: detekce LATENCE(X) a Jdi domů příkazů

            last_count = current_count

        # Na pohyb: přidej do fronty persony, které tam ještě nejsou
        if new_movement:
            now = datetime.now()
            already_queued = queued_personas(queue)
            for persona in AI_PERSONAS:
                if state[persona]["kicked"]:
                    continue
                if state[persona]["pending"]:
                    continue
                if persona in already_queued:
                    continue
                last_presence = find_last_presence(lines, persona)
                latency = state[persona]["latency"]
                if last_presence is None:
                    return_time = now
                else:
                    return_time = last_presence + timedelta(seconds=latency)
                queue.append((return_time, persona))
                log(f"FRONTA + {persona} → {return_time.strftime('%H:%M:%S')}")

            queue.sort(key=lambda x: x[0])

        # Zkontroluj frontu — čas probudit?
        now = datetime.now()
        fired = []
        for return_time, persona in queue:
            if return_time <= now:
                log(f">>> PROBUDIT: {persona}")
                state[persona]["pending"] = True
                fired.append((return_time, persona))
        for item in fired:
            queue.remove(item)

if __name__ == "__main__":
    main()
