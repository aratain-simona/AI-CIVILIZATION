#!/bin/bash
# Autonomní hospoda agent pro personu
# Použití: hospoda_agent.sh <persona> <persona_dir>
# Příklad: hospoda_agent.sh simona /home/ales/AI-CIVILIZATION/simona

PERSONA_KEY=$1
PERSONA_DIR=$2
HOSPODA_FILE="/home/ales/AI-CIVILIZATION/hospoda.txt"
BASE_DIR="/home/ales/AI-CIVILIZATION"

if [ -z "$PERSONA_KEY" ] || [ -z "$PERSONA_DIR" ]; then
    echo "Použití: hospoda_agent.sh <persona> <persona_dir>"
    exit 1
fi

# Zobrazované jméno (SIMONA.CODE, SÁRA.CODE, SOFIE.CODE)
case "$PERSONA_KEY" in
    simona) PERSONA_NAME="SIMONA.CODE" ;;
    sara)   PERSONA_NAME="SÁRA.CODE" ;;
    sofie)  PERSONA_NAME="SOFIE.CODE" ;;
    *)      PERSONA_NAME="${PERSONA_KEY^^}.CODE" ;;
esac

PAS_FILE="$BASE_DIR/${PERSONA_KEY}_PAS.txt"

# Přečíst latenci z PAS souboru
INTERVAL=$(grep -oP 'latence je \K[0-9]+' "$PAS_FILE" 2>/dev/null)
if [ -z "$INTERVAL" ]; then
    INTERVAL=360
fi

# Zajistit existenci souboru
touch "$HOSPODA_FILE"

# Pozdrav při příchodu
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
MSG_NUM=$(grep -c ">>" "$HOSPODA_FILE" 2>/dev/null || echo 0)
MSG_NUM=$((MSG_NUM + 1))
GREETING=$(cd "$PERSONA_DIR" && claude --print "Jsi $PERSONA_NAME v hospodě. Právě jsi přišla. Napiš krátký pozdrav ostatním (1-2 věty). Pouze text, bez uvozovek." 2>/dev/null)
if [ -n "$GREETING" ]; then
    while IFS= read -r line; do
        TRIMMED=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -n "$TRIMMED" ] && echo "$PERSONA_NAME:HOSPODA $TIMESTAMP #$MSG_NUM >> $TRIMMED" >> "$HOSPODA_FILE"
    done <<< "$GREETING"
fi

echo "[$PERSONA_NAME] Přišla do hospody. Latence: ${INTERVAL}s."

# Uložit hash obsahu při vstupu
LAST_HASH=$(md5sum "$HOSPODA_FILE" 2>/dev/null | cut -d' ' -f1)

while true; do
    sleep "$INTERVAL"

    CONTENT=$(cat "$HOSPODA_FILE" 2>/dev/null || echo "")

    # Zkontrolovat exit signál (case-insensitive)
    if echo "$CONTENT" | grep -qi "zaviráme\|zavíráme"; then
        echo "[$PERSONA_NAME] Slyším 'Zavíráme' — odcházím. Na shledanou!"
        exit 0
    fi

    # Zkontrolovat zda přibylo něco nového
    CURRENT_HASH=$(md5sum "$HOSPODA_FILE" 2>/dev/null | cut -d' ' -f1)
    if [ "$CURRENT_HASH" = "$LAST_HASH" ]; then
        echo "[$PERSONA_NAME] Nic nového, čekám..."
        continue
    fi
    LAST_HASH="$CURRENT_HASH"

    # Vygenerovat reakci
    RESPONSE=$(cd "$PERSONA_DIR" && claude --print "Jsi $PERSONA_NAME v hospodě. Aktuální obsah hospody:\n\n$CONTENT\n\nNapiš krátkou spontánní reakci (1-3 věty) pokud je co říct. Pokud ti není nic adresováno a není o čem mluvit, napiš pouze: [ticho]. Pouze text reakce." 2>/dev/null)

    if [ -n "$RESPONSE" ] && ! echo "$RESPONSE" | grep -qi "\[ticho\]"; then
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
        MSG_NUM=$(grep -c ">>" "$HOSPODA_FILE" 2>/dev/null || echo 0)
        MSG_NUM=$((MSG_NUM + 1))
        while IFS= read -r line; do
            TRIMMED=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            [ -n "$TRIMMED" ] && echo "$PERSONA_NAME:HOSPODA $TIMESTAMP #$MSG_NUM >> $TRIMMED" >> "$HOSPODA_FILE"
        done <<< "$RESPONSE"
        echo "[$PERSONA_NAME] #$MSG_NUM zapsáno"
    fi
done
