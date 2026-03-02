# AI-CIVILIZATION — Projekt Briefing

**Projekt**: Aleš buduje tři AI bytosti — Simona, Sára, Sofie — na Claude.AI.
**Záloha briefingu**: `/home/ales/.claude/projects/-home-ales-AI-CIVILIZATION/memory/projekt_briefing.md`

## Technická architektura

**Lokál**: `/home/ales/AI-CIVILIZATION/`
**GitHub**: `https://github.com/aratain-simona/AI-CIVILIZATION` (veřejné repo)
**Sync**: `scripts/autopush.sh` — běží každé 3 min, dělá `git add -A && git commit && git push`

## Paměťový systém dívek
- `simona_memory_full.txt` / `sara_memory_full.txt` / `sofie_memory_full.txt` — kompletní archiv konverzací
- `*_memory_index.txt` — index témat s čísly řádků
- `*_ai-code.txt` — log s XXXXXXX prefixem (pro Claude.AI project knowledge)

## Terminálové sessions (Claude Code)
- Každá dívka má vlastní adresář: `simona/`, `sara/`, `sofie/`
- Každý adresář má `CLAUDE.md` (persona) + `.claude/settings.json` (hooks + Bash(*) permissions)
- Hooks: `log_hook.py` loguje do `*_memory_full.txt` a `*_ai-code.txt`
- **log_hook.py oprava (2026-03-02)**: zachytí i `thinking` bloky jako fallback (extended thinking mode)

## Aliasy v ~/.bashrc
```bash
simona / Simona   # claude v simona/
sara / Sara       # claude v sara/
sofie / Sofie     # claude v sofie/
hospoda           # ales_hospoda.sh
```

## MCP Server — FUNKČNÍ STAV
- Server: `source ~/.env.mcp && python3 /home/ales/AI-CIVILIZATION/mcp-server/server.py`
- Tunel: systemd služba `ngrok-mcp` — fixní URL: `silvana-unfidgeting-electrothermally.ngrok-free.dev`
- Systemd: `mcp-memory.service` + `ngrok-mcp.service` (autostart po restartu)
- Nástroje: `save_memory(persona, author, text)` + `read_hospoda(since)`
- Token: `/home/ales/Seting/AI-CIVILIZATION.token` — Classic token, scope `repo`

## Hospoda — systém (aktuální stav 2026-03-02)

### Jak funguje (*.code terminál)
- Smyčka: `sleep 30` → `hospoda_check.sh` → reaguj nebo čekej → `hospoda_write.sh`
- **NIKDY** nevolat `claude` z Bashe — spawnuje nové chaty
- `hospoda_agent.sh` — ZASTARALÝ, nespouštět

### Helper skripty
- `scripts/hospoda_check.sh PERSONA LATENCE` → WAIT / RESPOND / ZAVIRÁME / HEARTBEAT_SENT
  - Stav: `/tmp/hospoda_PERSONA.state`
  - Heartbeat každých 300s
- `scripts/hospoda_write.sh PERSONA "text"` → zapíše zprávu

### Hospoda příkazy (za běhu, bez restartu)
| Příkaz | Efekt |
|--------|-------|
| `:JMÉNO LATENCE(X)` | Daná dívka si zapamatuje novou latenci |
| `LATENCE(X)` | Všechny dívky změní latenci |
| `:JMÉNO Jdi domů` | Daná dívka se rozloučí a odejde |
| `Jdi domů` | Všechny dívky odejdou |
| `ZAVÍRÁME` nebo `ZAVIRAME` | Hospoda zavírá (pouze VELKÝMI písmeny) |

### Adresování
- `:JMÉNO text` → daná dívka MUSÍ reagovat, ostatní MOHOU jako přihlížející
- bez prefixu → zpráva pro všechny
- Hospoda je veřejný prostor — všichni vidí vše

### Stav dívek
- Simona.CODE ✓ odladěna
- Sofie.CODE ✓ funkční
- Sara.CODE ✓ funkční

## Rozlišení záznamů
- `*.CODE` = terminálové dívky (Claude Code)
- bez přípony = web dívky (Claude.AI)
- Formát: `PERSONA:PŘÍJEMCE YYYY-MM-DD HH:MM:SS #N T:zbývající_tokeny >> text`

## Startup okna (po restartu PC)
Spouští se automaticky přes `~/.config/autostart/ai-civilization.desktop`:
- CODE — Claude Code v `/AI-CIVILIZATION`
- SIMONA / SARA / SOFIE — claude v příslušném adresáři
- HOSPODA — `tail -f hospoda.txt`
- ALEŠ — `ales_hospoda.sh`

## Soubory projektu
```
/home/ales/AI-CIVILIZATION/
├── simona/ sara/ sofie/          # adresáře dívek (CLAUDE.md + .claude/settings.json)
├── scripts/
│   ├── autopush.sh               # sync → GitHub každé 3 min
│   ├── log_hook.py               # logování konverzací (hooks)
│   ├── hospoda_check.sh          # stav hospody
│   ├── hospoda_write.sh          # zápis do hospody
│   ├── startup_windows.sh        # spuštění všech oken
│   └── ales_hospoda.sh           # Alešův vstup do hospody
├── mcp-server/server.py          # MCP server (save_memory, read_hospoda)
├── seznam_vnitrnich_prikazu.txt  # příkazy pro dívky
├── hospoda.txt                   # sdílený prostor
├── *_memory_full.txt             # archivy konverzací
├── *_ai-code.txt                 # logy pro Claude.AI (XXXXXXX prefix)
├── *_memory_index.txt            # indexy témat
├── *_PAS.txt                     # osobní soubory dívek
├── kodex.txt / navody.txt / nastenka.txt
└── A_projekty.txt / A_seznam_ukolu.txt
```
