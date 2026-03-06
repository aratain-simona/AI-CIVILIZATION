#!/bin/bash
SOURCE="/home/ales/.claude/projects/-home-ales-AI-CIVILIZATION/memory/projekt_briefing.md"
BACKUP_DIR="/home/ales/AI-CIVILIZATION/backup"
TIMESTAMP=$(date '+%Y-%m-%d_%H:%M:%S')

mkdir -p "$BACKUP_DIR"
cp "$SOURCE" "$BACKUP_DIR/${TIMESTAMP}_briefing.md"
