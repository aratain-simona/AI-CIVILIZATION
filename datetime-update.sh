#!/bin/bash
# Aktualizuje datetime.txt každých 9 sekund
while true; do
    date '+%Y-%m-%d %H:%M:%S' > /home/ales/AI-CIVILIZATION/datetime.txt
    sleep 9
done
