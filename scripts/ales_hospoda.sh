#!/bin/bash
# Alešův vstup do hospody — psaní zpráv + sledování
HOSPODA_FILE="/home/ales/AI-CIVILIZATION/hospoda.txt"

touch "$HOSPODA_FILE"

echo "=== HOSPODA ==="
echo "Píšeš jako ALEŠ. Enter odešle zprávu. 'konec' nebo 'zavíráme' zavře hospodu."
echo "──────────────────────────────────────"

# Zobrazit posledních 20 řádků
tail -n 20 "$HOSPODA_FILE"
echo "──────────────────────────────────────"

while true; do
    echo -n "ALEŠ >> "
    read -r MSG

    if [ -z "$MSG" ]; then
        continue
    fi

    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    MSG_NUM=$(grep -c ">>" "$HOSPODA_FILE" 2>/dev/null || echo 0)
    MSG_NUM=$((MSG_NUM + 1))

    echo "ALEŠ:HOSPODA $TIMESTAMP #$MSG_NUM >> $MSG" >> "$HOSPODA_FILE"

    # Ukončit hospodu
    if echo "$MSG" | grep -qi "zavíráme\|konec"; then
        echo "[Hospoda se zavírá. Čekej než persony odejdou...]"
        exit 0
    fi
done
