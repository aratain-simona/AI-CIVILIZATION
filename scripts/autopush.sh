#!/bin/bash
cd /home/ales/AI-CIVILIZATION || exit 1

# Nejdřív commitnout lokální změny (včetně autopush.log)
if ! git diff --quiet || ! git diff --cached --quiet; then
    git add -A
    git commit -m "auto: $(date '+%Y-%m-%d %H:%M:%S')"
fi

# Pushnout (MCP server nyní píše lokálně — pull není potřeba)
git push 2>&1
