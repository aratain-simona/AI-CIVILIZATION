#!/bin/bash
# hospoda_check.sh LAST_SEEN LAST_RESPONSE LATENCE ENTRY_COUNT
# Výstup: "WAIT" / "RESPOND: N nových zpráv" / "ZAVIRÁME"
# Návratový kód: 0=respond, 1=wait, 2=zaviráme

LAST_SEEN=${1:-0}
LAST_RESPONSE=${2:-0}
LATENCE=${3:-360}
ENTRY_COUNT=${4:-$LAST_SEEN}
HOSPODA=/home/ales/AI-CIVILIZATION/hospoda.txt

CURRENT=$(grep -cF ">>" "$HOSPODA" 2>/dev/null || echo 0)
NOW=$(date +%s)
ELAPSED=$(( NOW - LAST_RESPONSE ))

# ZAVIRÁME check — jen zprávy po příchodu
TAIL_COUNT=$(( CURRENT - ENTRY_COUNT ))
if [ "$TAIL_COUNT" -gt 0 ]; then
    if tail -n "$TAIL_COUNT" "$HOSPODA" | grep -qiE "zavir|zavír"; then
        echo "ZAVIRÁME"
        exit 2
    fi
fi

# Nic nového nebo příliš brzy
if [ "$CURRENT" -le "$LAST_SEEN" ] || [ "$ELAPSED" -lt "$LATENCE" ]; then
    echo "WAIT CURRENT=$CURRENT ELAPSED=${ELAPSED}s LATENCE=${LATENCE}s"
    exit 1
fi

# Jsou nové zprávy a uplynula latence — zobraz je
NEW=$(( CURRENT - LAST_SEEN ))
echo "RESPOND: $NEW nových zpráv (CURRENT=$CURRENT)"
echo "--- NOVÉ ZPRÁVY ---"
tail -n "$NEW" "$HOSPODA"
echo "--- KONEC ---"
echo "CURRENT=$CURRENT"
exit 0
