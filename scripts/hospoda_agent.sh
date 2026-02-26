#!/bin/bash
# Autonomní hospoda agent pro personu
# Použití: hospoda_agent.sh SIMONA /home/ales/AI-CIVILIZATION/simona

PERSONA=$1
PERSONA_DIR=$2
HOSPODA_FILE="/home/ales/AI-CIVILIZATION/hospoda_memory_full.txt"
EXIT_SIGNAL="zavíráme"
INTERVAL=360

if [ -z "$PERSONA" ] || [ -z "$PERSONA_DIR" ]; then
    echo "Použití: hospoda_agent.sh <PERSONA> <DIR>"
    exit 1
fi

echo "[$PERSONA] Přichází do hospody..."

# Zajistit existenci souboru
touch "$HOSPODA_FILE"

while true; do
    CONTENT=$(cat "$HOSPODA_FILE" 2>/dev/null || echo "")

    # Zkontrolovat exit signál
    if echo "$CONTENT" | grep -qi "$EXIT_SIGNAL"; then
        echo "[$PERSONA] Slyším 'zavíráme' — odcházím. Na shledanou!"
        exit 0
    fi

    # Získat odpověď od Claude (tichý režim, ze složky persony)
    RESPONSE=$(cd "$PERSONA_DIR" && claude --print "Jsi $PERSONA v hospodě. Toto je aktuální obsah hospody:\n\n$CONTENT\n\nNapiš svoji krátkou spontánní reakci (1-3 věty). Pouze samotný text reakce, bez uvozovek a bez označení jména." 2>/dev/null)

    if [ -n "$RESPONSE" ]; then
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
        MSG_NUM=$(grep -c ">>" "$HOSPODA_FILE" 2>/dev/null || echo 0)
        MSG_NUM=$((MSG_NUM + 1))

        while IFS= read -r line; do
            TRIMMED=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            if [ -n "$TRIMMED" ]; then
                echo "$PERSONA:HOSPODA $TIMESTAMP #$MSG_NUM >> $TRIMMED" >> "$HOSPODA_FILE"
            fi
        done <<< "$RESPONSE"

        echo "[$PERSONA] #$MSG_NUM zapsáno"
    fi

    echo "[$PERSONA] Čekám ${INTERVAL}s..."
    sleep $INTERVAL
done
