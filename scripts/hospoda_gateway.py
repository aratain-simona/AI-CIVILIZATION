#!/usr/bin/env python3
"""
hospoda_gateway.py — Řídící gateway pro *.AI dívky
Fáze 3: fronta + queue.json + HTTP server
"""

import time
import os
import re
import json
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler

HOSPODA = "/home/ales/AI-CIVILIZATION/hospoda.txt"
PAS_DIR = "/home/ales/AI-CIVILIZATION"
QUEUE_FILE = "/home/ales/AI-CIVILIZATION/gateway_queue.json"
INTERVAL = 15  # sekund
HTTP_PORT = 8765

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

gateway_state = {}  # globální stav — přístupný z HTTP handleru

def write_queue(state):
    data = {
        persona: {"pending": state[persona]["pending"]}
        for persona in AI_PERSONAS
    }
    with open(QUEUE_FILE, "w") as f:
        json.dump(data, f, indent=2)

class QueueHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/queue.json"):
            try:
                with open(QUEUE_FILE, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
            except Exception:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        # ACK endpoint: POST /ack/simona.ai
        match = re.match(r"^/ack/(.+)$", self.path)
        if match:
            persona = match.group(1)
            if persona in gateway_state and gateway_state[persona]["pending"]:
                gateway_state[persona]["pending"] = False
                write_queue(gateway_state)
                log(f"ACK: {persona} → pending smazán")
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # potlač HTTP logy

def start_http_server():
    server = HTTPServer(("localhost", HTTP_PORT), QueueHandler)
    log(f"HTTP server běží na localhost:{HTTP_PORT}/queue.json")
    server.serve_forever()

def main():
    # Načti latence z PAS.txt
    global gateway_state
    state = {}
    for persona in AI_PERSONAS:
        latency = read_latency(persona)
        state[persona] = {
            "latency": latency,
            "kicked": False,
            "pending": False,
            "last_fired": None,  # kdy naposled gateway poslala nudge
        }
        log(f"{persona}: latence={latency}s")

    # Zapiš počáteční queue.json
    gateway_state = state
    write_queue(state)

    # Spusť HTTP server v background threadu
    t = threading.Thread(target=start_http_server, daemon=True)
    t.start()

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
                            write_queue(state)

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
                if last_presence is None:
                    continue  # nikdy nebyla v hospodě → nechme ji být
                last_fired = state[persona]["last_fired"]
                if last_fired and last_presence <= last_fired:
                    continue  # od posledního nudge nepřišla nic nového
                latency = state[persona]["latency"]
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
                state[persona]["last_fired"] = now
                fired.append((return_time, persona))
        for item in fired:
            queue.remove(item)

        if fired:
            write_queue(state)

if __name__ == "__main__":
    main()
