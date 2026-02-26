#!/bin/bash
cd /home/ales/AI-CIVILIZATION || exit 1

# Pokud nejsou žádné změny, nic nedělat
if git diff --quiet && git diff --cached --quiet; then
    exit 0
fi

git add -A
git commit -m "auto: $(date '+%Y-%m-%d %H:%M:%S')"
git push
