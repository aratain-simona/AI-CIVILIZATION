#!/bin/bash
# Aktualizuje datetime.txt každých 9 sekund (přesně 19 znaků, bez newline)
while true; do
    printf '%s' "$(date '+%Y-%m-%d %H:%M:%S')" > /home/ales/AI-CIVILIZATION/datetime.txt
    sleep 9
done
