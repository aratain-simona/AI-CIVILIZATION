#!/bin/bash
# Aktualizuje datetime.file každých 9 sekund (přesně 19 znaků, bez newline)
# *.CODE: cat /home/ales/AI-CIVILIZATION/datetime.file
# *.AI:   read_file(persona="datetime")
while true; do
    printf '%s' "$(date '+%Y-%m-%d %H:%M:%S')" > /home/ales/AI-CIVILIZATION/datetime.file
    sleep 9
done
