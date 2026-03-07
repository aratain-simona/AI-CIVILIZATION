#!/bin/bash
# Aktualizuje datetime.txt a datetime.file každých 9 sekund (přesně 19 znaků, bez newline)
while true; do
    DT="$(date '+%Y-%m-%d %H:%M:%S')"
    printf '%s' "$DT" > /home/ales/AI-CIVILIZATION/datetime.txt
    printf '%s' "$DT" > /home/ales/AI-CIVILIZATION/datetime.file
    sleep 9
done
