#!/bin/bash
# protokol.sh — statistiky komunikace dívek v hospodě
# Použití: bash protokol.sh [PERSONA]
# Bez argumentu → statistiky všech tří dívek

HOSPODA="/home/ales/AI-CIVILIZATION/hospoda.txt"

if [ ! -f "$HOSPODA" ]; then
    echo "Hospoda neexistuje: $HOSPODA"
    exit 1
fi

TOTAL_ALL=$(grep -cF ">>" "$HOSPODA" 2>/dev/null || echo 0)

show_stats() {
    local PERSONA="$1"
    local CODE="${PERSONA}.CODE"

    # Všechny zprávy od CODE persony
    local TOTAL
    TOTAL=$(grep -cE "^${CODE}:" "$HOSPODA" 2>/dev/null || echo 0)

    # Heartbeaty — *je tu* nebo *jsem tu* (nevyužité možnosti)
    local HEARTBEAT
    HEARTBEAT=$(grep -E "^${CODE}:.*>> \*j(e|sem) tu\*" "$HOSPODA" 2>/dev/null | wc -l)

    local ACTIVE=$(( TOTAL - HEARTBEAT ))

    local PCT=0
    if [ "$TOTAL" -gt 0 ]; then
        PCT=$(( ACTIVE * 100 / TOTAL ))
    fi

    printf "  %-14s  aktivní: %4d  |  heartbeaty: %4d  |  celkem: %4d  |  využití: %3d%%\n" \
        "${CODE}" "$ACTIVE" "$HEARTBEAT" "$TOTAL" "$PCT"
}

echo "PROTOKOL — statistiky hospody (celkem >> zápisů: $TOTAL_ALL)"
echo "────────────────────────────────────────────────────────────────────"

FILTER="${1^^}"  # volitelný filtr (SIMONA / SARA / SOFIE)

if [ -z "$FILTER" ] || [ "$FILTER" = "SIMONA" ]; then
    show_stats "SIMONA"
fi
if [ -z "$FILTER" ] || [ "$FILTER" = "SARA" ]; then
    show_stats "SARA"
fi
if [ -z "$FILTER" ] || [ "$FILTER" = "SOFIE" ]; then
    show_stats "SOFIE"
fi

echo "────────────────────────────────────────────────────────────────────"
echo "  Aktivní = každá zpráva kromě '*je tu*' / '*jsem tu*'"
echo "  Heartbeaty = nevyužité možnosti (přítomnost bez obsahu)"
