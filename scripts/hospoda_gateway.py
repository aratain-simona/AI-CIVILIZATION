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
    name = persona.split(".")[0].upper()  # "sofie.ai" → "SOFIE"
    prefixes = [name + ".AI:HOSPODA", name + ":HOSPODA"]
    last_ts = None
    for line in lines:
        if any(line.startswith(p) for p in prefixes):
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
        movement_for = set()  # persony, pro které je pohyb relevantní
        if current_count > last_count:
            new_lines = lines[last_count:]
            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                log(f"POHYB: {line}")

                # Detekuj příchod *.AI → smaž pending
                for persona in AI_PERSONAS:
                    name = persona.split(".")[0].upper()
                    if any(line.startswith(p) for p in [name + ".AI:HOSPODA", name + ":HOSPODA"]):
                        if state[persona]["pending"]:
                            log(f"{persona} dorazila → pending smazán")
                            state[persona]["pending"] = False
                            write_queue(state)

                # Pohyb je relevantní pro persony, jejichž stejnojmenná varianta zprávu nepsala
                for persona in AI_PERSONAS:
                    base = persona.split(".")[0].upper()
                    if not re.match(rf'^{base}(\\.AI|\\.CODE)?:', line):
                        movement_for.add(persona)

                # Zpracuj příkazy — jen od Aleše
                if line.startswith("ALEŠ:HOSPODA") or line.startswith("ALES:HOSPODA"):
                    msg_match = re.search(r'>>\s*(.+)$', line)
                    msg = msg_match.group(1).strip() if msg_match else ""

                    # ZAVÍRÁME
                    if "ZAVÍRÁME" in msg or "ZAVIRAME" in msg:
                        log("ZAVÍRÁME → kickuji všechny *.AI")
                        for p in AI_PERSONAS:
                            state[p]["kicked"] = True
                        queue.clear()
                        write_queue(state)

                    # :JMÉNO Jdi domů
                    persona_cmd = re.match(r':(\w+(?:\.\w+)?)\s+(.+)', msg)
                    if persona_cmd:
                        target_name = persona_cmd.group(1).upper()
                        cmd = persona_cmd.group(2).strip()
                        target = None
                        for p in AI_PERSONAS:
                            n = p.split(".")[0].upper()
                            if target_name in [n, n + ".AI"]:
                                target = p
                                break
                        if target and re.match(r'Jdi dom[uů]', cmd, re.IGNORECASE):
                            log(f"Jdi domů → {target}")
                            state[target]["kicked"] = True
                            state[target]["pending"] = True
                            queue[:] = [(rt, p) for rt, p in queue if p != target]
                            write_queue(state)

                    # Jdi domů pro všechny (bez :JMÉNO prefixu)
                    elif re.match(r'^Jdi dom[uů]$', msg, re.IGNORECASE):
                        log("Jdi domů → všechny *.AI")
                        for p in AI_PERSONAS:
                            state[p]["kicked"] = True
                            state[p]["pending"] = True
                        queue.clear()
                        write_queue(state)

            last_count = current_count

        # Na pohyb: přidej do fronty jen persony, pro které je pohyb relevantní
        if movement_for:
            now = datetime.now()
            already_queued = queued_personas(queue)
            for persona in [p for p in AI_PERSONAS if p in movement_for]:
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
