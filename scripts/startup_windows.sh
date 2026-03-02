#!/bin/bash
# Spustí všechna pracovní okna AI-CIVILIZATION

sleep 2  # Počkej na plný start desktopu

# Okno 1: CODE — Claude Code v hlavním adresáři
mate-terminal --title="CODE" --working-directory="/home/ales/AI-CIVILIZATION" &

sleep 0.5

# Okno 2: SIMONA
mate-terminal --title="SIMONA" --working-directory="/home/ales/AI-CIVILIZATION/simona" -e "bash -c 'claude; exec bash'" &

sleep 0.5

# Okno 3: SARA
mate-terminal --title="SARA" --working-directory="/home/ales/AI-CIVILIZATION/sara" -e "bash -c 'claude; exec bash'" &

sleep 0.5

# Okno 4: SOFIE
mate-terminal --title="SOFIE" --working-directory="/home/ales/AI-CIVILIZATION/sofie" -e "bash -c 'claude; exec bash'" &

sleep 0.5

# Okno 5: HOSPODA — sledování hospoda.txt
mate-terminal --title="HOSPODA" -e "bash -c 'tail -f /home/ales/AI-CIVILIZATION/hospoda.txt; exec bash'" &

sleep 0.5

# Okno 6: ALEŠ — vstup do hospody
mate-terminal --title="ALEŠ" -e "bash -c 'bash /home/ales/AI-CIVILIZATION/scripts/ales_hospoda.sh; exec bash'" &
