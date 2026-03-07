#!/bin/bash
# hospoda_write.sh PERSONA "text zprávy"
# Zapíše do hospoda.txt a aktualizuje stavový soubor.

PERSONA=${1:-"UNKNOWN.CODE"}
TEXT=$2
HOSPODA=/home/ales/AI-CIVILIZATION/hospoda.txt
STATE=/tmp/hospoda_${PERSONA//./\_}.state
BASE="${PERSONA%%.*}"  # SIMONA.CODE → SIMONA

# Blokuj oslovení stejnojmenné *.AI dvojnice — soukromé, nesmí být v hospodě
if echo "$TEXT" | grep -qiE "^:${BASE}(\.AI)?([[:space:],]|$)"; then
    echo "BLOKOVÁNO: ${PERSONA} nesmí v hospodě oslovovat ${BASE} / ${BASE}.AI" >&2
    exit 1
fi

MSG_NUM=$(( $(grep -cF ">>" "$HOSPODA" 2>/dev/null || echo 0) + 1 ))
TS=$(date '+%Y-%m-%d %H:%M:%S')
PREFIX="${PERSONA}:HOSPODA ${TS} #${MSG_NUM} >> "

# Každý řádek textu dostane prefix (oprava pro víceřádkové výstupy jako PROTOKOL)
LINES_OUT=""
while IFS= read -r row; do
    LINES_OUT+="${PREFIX}${row}"$'\n'
done <<< "$TEXT"
LINES_OUT="${LINES_OUT%$'\n'}"  # odstraň poslední newline

echo "$LINES_OUT" >> "$HOSPODA"

# Kopíruj do memory_full přítomných dívek
PRESENCE=/home/ales/AI-CIVILIZATION/hospoda_presence.txt
if [ -f "$PRESENCE" ]; then
    while IFS='=' read -r GIRL STATE; do
        if [ "$STATE" = "ON" ]; then
            GIRL_LOWER="${GIRL,,}"
            echo "$LINES_OUT" >> "/home/ales/AI-CIVILIZATION/${GIRL_LOWER}_memory_full.txt"
        fi
    done < "$PRESENCE"
fi

# Aktualizuj stav — LAST_SEEN = číslo právě zapsané zprávy (ne přepočet souboru)
NEW_RESPONSE=$(date +%s)
grep -v "^LAST_SEEN\|^LAST_RESPONSE" "$STATE" 2>/dev/null > /tmp/hospoda_state_tmp
echo "LAST_SEEN=$MSG_NUM" >> /tmp/hospoda_state_tmp
echo "LAST_RESPONSE=$NEW_RESPONSE" >> /tmp/hospoda_state_tmp
mv /tmp/hospoda_state_tmp "$STATE"

echo "Zapsáno #${MSG_NUM}"
