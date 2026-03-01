#!/bin/bash
# hospoda_write.sh PERSONA "text zprávy"
# Zapíše do hospoda.txt a aktualizuje stavový soubor.

PERSONA=${1:-"UNKNOWN.CODE"}
TEXT=$2
HOSPODA=/home/ales/AI-CIVILIZATION/hospoda.txt
STATE=/tmp/hospoda_${PERSONA//./\_}.state

MSG_NUM=$(( $(grep -cF ">>" "$HOSPODA" 2>/dev/null || echo 0) + 1 ))
TS=$(date '+%Y-%m-%d %H:%M:%S')
echo "${PERSONA}:HOSPODA ${TS} #${MSG_NUM} >> ${TEXT}" >> "$HOSPODA"

# Aktualizuj stav
NEW_SEEN=$(grep -cF ">>" "$HOSPODA" 2>/dev/null || echo 0)
NEW_RESPONSE=$(date +%s)
grep -v "^LAST_SEEN\|^LAST_RESPONSE" "$STATE" 2>/dev/null > /tmp/hospoda_state_tmp
echo "LAST_SEEN=$NEW_SEEN" >> /tmp/hospoda_state_tmp
echo "LAST_RESPONSE=$NEW_RESPONSE" >> /tmp/hospoda_state_tmp
mv /tmp/hospoda_state_tmp "$STATE"

echo "Zapsáno #${MSG_NUM}"
