#!/bin/bash
# Záloha celého projektu AI-CIVILIZATION + vše potřebné pro plnou obnovu
# Scénář: nový počítač, přihlásit se, obnovit z backupu → vše běží
BACKUP_DIR="/home/ales/AI-CIVILIZATION/backup"
TIMESTAMP=$(date '+%Y-%m-%d_%H:%M:%S')
ZIPFILE="$BACKUP_DIR/${TIMESTAMP}_project_complette.zip"

mkdir -p "$BACKUP_DIR"

# --- 1. Hlavní projekt (bez backup/ a .git/ — ty jsou velké a nepotřebné) ---
zip -r "$ZIPFILE" /home/ales/AI-CIVILIZATION/ \
    --exclude "*/backup/*" \
    --exclude "*/.git/*" \
    -q

# --- 2. Systemd služby (všechny projektové) ---
zip "$ZIPFILE" \
    /etc/systemd/system/mcp-memory.service \
    /etc/systemd/system/ngrok-mcp.service \
    /etc/systemd/system/autopush-loop.service \
    /etc/systemd/system/hospoda-gateway.service \
    /etc/systemd/system/backup-briefing.service \
    /etc/systemd/system/backup-briefing.timer \
    /etc/systemd/system/datetime-update.service \
    /etc/systemd/system/memory-cleaner.service \
    2>/dev/null -q

# --- 3. Autostart (spuštění všech oken po restartu PC) ---
zip "$ZIPFILE" \
    /home/ales/.config/autostart/ai-civilization.desktop \
    2>/dev/null -q

# --- 4. Tokeny, env soubory, bash ---
zip "$ZIPFILE" \
    /home/ales/.env.mcp \
    /home/ales/.env.mcp.systemd \
    /home/ales/Seting/AI-CIVILIZATION.token \
    /home/ales/.bashrc \
    2>/dev/null -q

# --- 5. Claude Code konfigurace (MCP permissions) ---
zip "$ZIPFILE" \
    /home/ales/.claude/settings.local.json \
    2>/dev/null -q

# --- 6. ngrok konfigurace (auth token) ---
zip "$ZIPFILE" \
    /home/ales/snap/ngrok/350/.config/ngrok/ngrok.yml \
    2>/dev/null -q

echo "Záloha vytvořena: $ZIPFILE"
echo "Velikost: $(du -sh "$ZIPFILE" | cut -f1)"
echo ""
echo "Obsah zálohy:"
echo "  OK  AI-CIVILIZATION/ (projekt + chrome-extension + skripty)"
echo "  OK  systemd sluzby (mcp, ngrok, autopush, hospoda, datetime-update, memory-cleaner)"
echo "  OK  autostart (ai-civilization.desktop)"
echo "  OK  .env.mcp, tokeny, .bashrc"
echo "  OK  .claude/settings.local.json (MCP permissions)"
echo "  OK  ngrok.yml (auth token)"
