#!/bin/bash
# hospoda_check.sh PERSONA LATENCE
# Stav si pamatuje v /tmp/hospoda_PERSONA.state
# Výstup: "WAIT" / "RESPOND" + nové zprávy / "ZAVIRÁME"
# Použití: bash hospoda_check.sh SIMONA.CODE 60

PERSONA=${1:-"UNKNOWN.CODE"}
LATENCE=${2:-360}
HOSPODA=/home/ales/AI-CIVILIZATION/hospoda.txt
STATE=/tmp/hospoda_${PERSONA//./\_}.state

# Načti nebo inicializuj stav
if [ -f "$STATE" ]; then
    source "$STATE"
else
    LAST_SEEN=$(grep -cF ">>" "$HOSPODA" 2>/dev/null || echo 0)
    LAST_RESPONSE=0
    ENTRY_COUNT=$LAST_SEEN
    echo "LAST_SEEN=$LAST_SEEN" > "$STATE"
    echo "LAST_RESPONSE=$LAST_RESPONSE" >> "$STATE"
    echo "ENTRY_COUNT=$ENTRY_COUNT" >> "$STATE"
fi

CURRENT=$(grep -cF ">>" "$HOSPODA" 2>/dev/null || echo 0)
NOW=$(date +%s)
ELAPSED=$(( NOW - LAST_RESPONSE ))

# ZAVIRÁME check — jen zprávy po příchodu
TAIL_COUNT=$(( CURRENT - ENTRY_COUNT ))
if [ "$TAIL_COUNT" -gt 0 ]; then
    if tail -n "$TAIL_COUNT" "$HOSPODA" | grep -qiE "zavir|zavir"; then
        echo "ZAVIRÁME"
        rm -f "$STATE"
        exit 2
    fi
fi

# Nic nového nebo příliš brzy
if [ "$CURRENT" -le "$LAST_SEEN" ] || [ "$ELAPSED" -lt "$LATENCE" ]; then
    echo "WAIT CURRENT=$CURRENT LAST_SEEN=$LAST_SEEN ELAPSED=${ELAPSED}s LATENCE=${LATENCE}s"
    exit 1
fi

# Nové zprávy a latence uplynula
NEW=$(( CURRENT - LAST_SEEN ))
echo "RESPOND: $NEW nových zpráv"
echo "--- NOVÉ ZPRÁVY ---"
tail -n "$NEW" "$HOSPODA"
echo "---"
exit 0
