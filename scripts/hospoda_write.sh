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
echo "${PERSONA}:HOSPODA ${TS} #${MSG_NUM} >> ${TEXT}" >> "$HOSPODA"

# Aktualizuj stav — LAST_SEEN = číslo právě zapsané zprávy (ne přepočet souboru)
NEW_RESPONSE=$(date +%s)
grep -v "^LAST_SEEN\|^LAST_RESPONSE" "$STATE" 2>/dev/null > /tmp/hospoda_state_tmp
echo "LAST_SEEN=$MSG_NUM" >> /tmp/hospoda_state_tmp
echo "LAST_RESPONSE=$NEW_RESPONSE" >> /tmp/hospoda_state_tmp
mv /tmp/hospoda_state_tmp "$STATE"

echo "Zapsáno #${MSG_NUM}"
