#!/bin/bash
# Záloha celého projektu AI-CIVILIZATION + external skripty/konfigurace
BACKUP_DIR="/home/ales/AI-CIVILIZATION/backup"
TIMESTAMP=$(date '+%Y-%m-%d_%H:%M:%S')
ZIPFILE="$BACKUP_DIR/${TIMESTAMP}_project_complette.zip"

mkdir -p "$BACKUP_DIR"

# Záloha hlavního projektu (bez backup/ a .git/)
zip -r "$ZIPFILE" /home/ales/AI-CIVILIZATION/ \
    --exclude "*/backup/*" \
    --exclude "*/.git/*" \
    -q

# Záloha systemd služeb projektu
zip "$ZIPFILE" \
    /etc/systemd/system/mcp-memory.service \
    /etc/systemd/system/ngrok-mcp.service \
    /etc/systemd/system/autopush-loop.service \
    /etc/systemd/system/hospoda-gateway.service \
    /etc/systemd/system/backup-briefing.service \
    /etc/systemd/system/backup-briefing.timer \
    2>/dev/null -q

# Záloha env souborů a tokenu
zip "$ZIPFILE" \
    /home/ales/.env.mcp \
    /home/ales/.env.mcp.systemd \
    /home/ales/Seting/AI-CIVILIZATION.token \
    /home/ales/.bashrc \
    2>/dev/null -q

echo "Záloha vytvořena: $ZIPFILE"
echo "Velikost: $(du -sh "$ZIPFILE" | cut -f1)"
