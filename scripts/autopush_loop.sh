#!/bin/bash
# autopush_loop.sh — spouští autopush.sh každých 15 sekund
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

while true; do
    bash "$SCRIPT_DIR/autopush.sh" >> "$SCRIPT_DIR/autopush.log" 2>&1
    sleep 15
done
