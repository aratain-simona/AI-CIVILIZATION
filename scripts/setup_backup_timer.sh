#!/bin/bash
cat > /etc/systemd/system/backup-briefing.service << 'EOF'
[Unit]
Description=Záloha projekt_briefing.md

[Service]
Type=oneshot
User=ales
ExecStart=/home/ales/AI-CIVILIZATION/scripts/backup_briefing.sh
EOF

cat > /etc/systemd/system/backup-briefing.timer << 'EOF'
[Unit]
Description=Záloha briefingu každých 30 minut

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable backup-briefing.timer
systemctl start backup-briefing.timer
systemctl status backup-briefing.timer --no-pager
