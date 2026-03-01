#!/bin/bash
# hospoda_write.sh JMENO.CODE "text zprávy"
# Zapíše řádek do hospoda.txt se správným číslem zprávy.

JMENO=${1:-"UNKNOWN.CODE"}
TEXT=$2
HOSPODA=/home/ales/AI-CIVILIZATION/hospoda.txt

MSG_NUM=$(( $(grep -cF ">>" "$HOSPODA" 2>/dev/null || echo 0) + 1 ))
TS=$(date '+%Y-%m-%d %H:%M:%S')
echo "${JMENO}:HOSPODA ${TS} #${MSG_NUM} >> ${TEXT}" >> "$HOSPODA"
echo "Zapsáno #${MSG_NUM}: ${TEXT}"
