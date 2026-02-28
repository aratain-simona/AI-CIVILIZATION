#!/bin/bash
cd /home/ales/AI-CIVILIZATION || exit 1

# Nejdřív commitnout lokální změny (včetně autopush.log)
if ! git diff --quiet || ! git diff --cached --quiet; then
    git add -A
    git commit -m "auto: $(date '+%Y-%m-%d %H:%M:%S')"
fi

# Pak stáhnout změny z GitHubu (MCP server mohl něco zapsat)
git pull --rebase origin master 2>&1

# Pushnout (lokální + stažené)
git push 2>&1
