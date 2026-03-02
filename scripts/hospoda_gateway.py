#!/usr/bin/env python3
"""
hospoda_gateway.py — Řídící gateway pro *.AI dívky
Fáze 1: detekce pohybu v hospoda.txt
"""

import time
import os
from datetime import datetime

HOSPODA = "/home/ales/AI-CIVILIZATION/hospoda.txt"
INTERVAL = 15  # sekund

def read_lines():
    if not os.path.exists(HOSPODA):
        return []
    with open(HOSPODA, "r") as f:
        return f.readlines()

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def main():
    log("Gateway spuštěna.")
    last_count = len(read_lines())
    log(f"Hospoda má {last_count} řádků.")

    while True:
        time.sleep(INTERVAL)
        lines = read_lines()
        current_count = len(lines)

        if current_count > last_count:
            new_lines = lines[last_count:]
            for line in new_lines:
                line = line.strip()
                if line:
                    log(f"POHYB: {line}")
            last_count = current_count

if __name__ == "__main__":
    main()
