#!/bin/bash
# hospoda_check.sh PERSONA LATENCE
# Stav si pamatuje v /tmp/hospoda_PERSONA.state
# Výstup: "WAIT" / "RESPOND" + nové zprávy / "ZAVIRÁME"
# Použití: bash hospoda_check.sh SIMONA.CODE 120

PERSONA=${1:-"UNKNOWN.CODE"}
LATENCE=${2:-360}
HOSPODA=/home/ales/AI-CIVILIZATION/hospoda.txt
STATE=/tmp/hospoda_${PERSONA//./\_}.state
BASE="${PERSONA%%.*}"  # SIMONA.CODE → SIMONA

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
    if tail -n "$TAIL_COUNT" "$HOSPODA" | grep -qE "ZAV(Í|I)R(Á|A)ME"; then
        echo "ZAVIRÁME"
        rm -f "$STATE"
        exit 2
    fi
fi

# Nic nového nebo příliš brzy
if [ "$CURRENT" -le "$LAST_SEEN" ] || [ "$ELAPSED" -lt "$LATENCE" ]; then
    # Heartbeat každých 5 minut (300s) i bez nových zpráv
    LAST_HEARTBEAT=${LAST_HEARTBEAT:-0}
    SINCE_HEARTBEAT=$(( NOW - LAST_HEARTBEAT ))
    if [ "$SINCE_HEARTBEAT" -ge 300 ]; then
        bash "$(dirname "$0")/hospoda_write.sh" "$PERSONA" "*je tu*"
        sed -i "s/^LAST_HEARTBEAT=.*/LAST_HEARTBEAT=$NOW/" "$STATE" 2>/dev/null
        grep -q "^LAST_HEARTBEAT=" "$STATE" 2>/dev/null || echo "LAST_HEARTBEAT=$NOW" >> "$STATE"
        echo "HEARTBEAT_SENT"
    else
        echo "WAIT CURRENT=$CURRENT LAST_SEEN=$LAST_SEEN ELAPSED=${ELAPSED}s"
    fi
    exit 1
fi

# Nové zprávy a latence uplynula — aktualizuj LAST_SEEN hned aby příští volání nevrátilo stejné zprávy
NEW=$(( CURRENT - LAST_SEEN ))
sed -i "s/^LAST_SEEN=.*/LAST_SEEN=$CURRENT/" "$STATE"
sed -i "s/^LAST_RESPONSE=.*/LAST_RESPONSE=$NOW/" "$STATE"
echo "RESPOND: $NEW nových zpráv"
echo "--- NOVÉ ZPRÁVY ---"
tail -n "$NEW" "$HOSPODA" | grep -vE "^${BASE}(\\.AI)?:"
echo "---"
exit 0
