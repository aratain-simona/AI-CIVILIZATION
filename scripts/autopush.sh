#!/bin/bash
cd /home/ales/AI-CIVILIZATION || exit 1

# Stáhnout změny z GitHubu (pokud claude.ai něco zapsal)
git pull --rebase origin master 2>&1

# Pokud jsou lokální změny, commitnout a pushnout
if ! git diff --quiet || ! git diff --cached --quiet; then
    git add -A
    git commit -m "auto: $(date '+%Y-%m-%d %H:%M:%S')"
    git push
fi
