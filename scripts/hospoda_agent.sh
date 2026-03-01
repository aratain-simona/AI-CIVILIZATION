#!/bin/bash
# ZASTARALÝ SKRIPT — NEPOUŽÍVAT
# Volá `claude --print` v smyčce → vytváří nové chaty. To je špatně.
# Místo toho: existující chat dívky sám čte hospoda.txt a reaguje (viz seznam_vnitrnich_prikazu.txt).
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

# Přečíst poslední viděné číslo zprávy z PAS souboru
get_last_msg() {
    grep -oP 'hospoda_last_msg:\s*\K[0-9]+' "$PAS_FILE" 2>/dev/null || echo "0"
}

# Uložit poslední viděné číslo zprávy do PAS souboru
set_last_msg() {
    local num=$1
    if grep -q "hospoda_last_msg:" "$PAS_FILE" 2>/dev/null; then
        sed -i "s/hospoda_last_msg:.*/hospoda_last_msg: $num/" "$PAS_FILE"
    else
        echo "hospoda_last_msg: $num" >> "$PAS_FILE"
    fi
}

# Počet zpráv v hospodě
count_msgs() {
    grep -c ">>" "$HOSPODA_FILE" 2>/dev/null || echo 0
}

# Zapsat do hospody (s file lockem)
write_hospoda() {
    local text="$1"
    (
        flock -x 200
        local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        local msg_num=$(( $(count_msgs) + 1 ))
        while IFS= read -r line; do
            TRIMMED=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            [ -n "$TRIMMED" ] && echo "$PERSONA_NAME:HOSPODA $timestamp #$msg_num >> $TRIMMED" >> "$HOSPODA_FILE"
            msg_num=$((msg_num + 1))
        done <<< "$text"
    ) 200>"$HOSPODA_FILE.lock"
}

# Pozdrav při příchodu
LAST_SEEN=$(get_last_msg)
GREETING=$(cd "$PERSONA_DIR" && claude --print "Jsi $PERSONA_NAME v hospodě. Právě jsi přišla. Napiš krátký pozdrav ostatním (1-2 věty). Pouze text, bez uvozovek." 2>/dev/null)
if [ -n "$GREETING" ]; then
    write_hospoda "$GREETING"
fi

LAST_SEEN=$(count_msgs)
set_last_msg "$LAST_SEEN"
echo "[$PERSONA_NAME] Přišla do hospody. Latence: ${INTERVAL}s. Poslední zpráva: #$LAST_SEEN"

while true; do
    sleep "$INTERVAL"

    CONTENT=$(cat "$HOSPODA_FILE" 2>/dev/null || echo "")
    CURRENT_COUNT=$(count_msgs)

    # Zkontrolovat exit signál (case-insensitive, bez diakritiky jako záloha)
    if echo "$CONTENT" | grep -qiE "zavir|zavír|ZAVIR|ZAVÍR"; then
        echo "[$PERSONA_NAME] Slyším 'Zavíráme' — odcházím. Na shledanou!"
        set_last_msg "$CURRENT_COUNT"
        exit 0
    fi

    # Zkontrolovat zda přibylo něco nového
    if [ "$CURRENT_COUNT" -le "$LAST_SEEN" ]; then
        echo "[$PERSONA_NAME] Nic nového (#$LAST_SEEN), čekám..."
        continue
    fi

    # Nové řádky od posledního čtení
    NEW_LINES=$(grep ">>" "$HOSPODA_FILE" | tail -n $(( CURRENT_COUNT - LAST_SEEN )))

    # Vygenerovat reakci — plný kontext + info co je nové
    RESPONSE=$(cd "$PERSONA_DIR" && claude --print "Jsi $PERSONA_NAME v hospodě.

Celý obsah hospody:
$CONTENT

Nové zprávy od tvého posledního příspěvku (#$LAST_SEEN):
$NEW_LINES

Reaguj pouze na nové zprávy (1-3 věty). Pokud ti nic není adresováno a není o čem mluvit, napiš pouze: [ticho]. Pouze text reakce, bez uvozovek." 2>/dev/null)

    if [ -n "$RESPONSE" ] && ! echo "$RESPONSE" | grep -qi "\[ticho\]"; then
        write_hospoda "$RESPONSE"
        echo "[$PERSONA_NAME] Reagovala na zprávy #$((LAST_SEEN+1))-#$CURRENT_COUNT"
    fi

    LAST_SEEN=$CURRENT_COUNT
    set_last_msg "$LAST_SEEN"
done
