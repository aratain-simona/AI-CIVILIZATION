#!/bin/bash
# Alešův vstup do hospody — psaní zpráv + sledování
HOSPODA_FILE="/home/ales/AI-CIVILIZATION/hospoda.txt"

PRESENCE_FILE="/home/ales/AI-CIVILIZATION/hospoda_presence.txt"

touch "$HOSPODA_FILE"

ZAVIRAJI=0

_odchod() {
    sed -i "s/^ALES=.*/ALES=OFF/" "$PRESENCE_FILE"
    if [ "$ZAVIRAJI" = "0" ]; then
        echo ""
        echo -n "ALEŠ >> "
        read -r ODCHOD_MSG </dev/tty
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
        if [ -n "$ODCHOD_MSG" ]; then
            MSG_NUM=$(( $(grep -cF ">>" "$HOSPODA_FILE" 2>/dev/null || echo 0) + 1 ))
            echo "ALEŠ:HOSPODA $TIMESTAMP #$MSG_NUM >> $ODCHOD_MSG" >> "$HOSPODA_FILE"
        fi
        MSG_NUM=$(( $(grep -cF ">>" "$HOSPODA_FILE" 2>/dev/null || echo 0) + 1 ))
        echo "ALEŠ:HOSPODA $TIMESTAMP #$MSG_NUM >> *Aleš odešel. Dívky zůstaly samy.*" >> "$HOSPODA_FILE"
    fi
}
trap '_odchod' EXIT

# Aleš vstupuje
sed -i "s/^ALES=.*/ALES=ON/" "$PRESENCE_FILE"

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
    MSG_NUM=$(grep -c ">>" "$HOSPODA_FILE" 2>/dev/null)
    MSG_NUM=${MSG_NUM:-0}
    MSG_NUM=$((MSG_NUM + 1))

    echo "ALEŠ:HOSPODA $TIMESTAMP #$MSG_NUM >> $MSG" >> "$HOSPODA_FILE"

    # Ukončit hospodu
    if echo "$MSG" | grep -qi "zavíráme\|konec"; then
        ZAVIRAJI=1
        echo "[Hospoda se zavírá. Čekej než persony odejdou...]"
        exit 0
    fi
done
