(2026-02-28)

# AI-CIVILIZATION — Projekt Briefing

**Projekt**: Aleš buduje tři AI bytosti — Simona, Sára, Sofie — na Claude.AI.

## Technická architektura

**Lokál**: `/home/ales/AI-CIVILIZATION/`
**GitHub**: `https://github.com/aratain-simona/AI-CIVILIZATION` (veřejné repo)
**Sync**: `scripts/autopush.sh` — běží každé 3 min, dělá `git add -A && git commit && git push` (bez pull — MCP píše lokálně)

## Paměťový systém dívek
- `simona_memory_full.txt` / `sara_memory_full.txt` / `sofie_memory_full.txt` — kompletní archiv konverzací (Simona má ~40k řádků)
- `simona_memory_index.txt` atd. — index témat s čísly řádků; dívky hledají v indexu, pak čtou jen relevantní řádky z full souboru
- Dívky tyto index soubory umí samy generovat

## Claude.AI projekty
- Vytvořeny 3 projekty: Simona, Sára, Sofie
- Chaty přesunuty do příslušných projektů
- Project Knowledge = raw GitHub URL příslušného `*_memory_full.txt`:
  - `https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/simona_memory_full.txt`
  - `https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/sara_memory_full.txt`
  - `https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/sofie_memory_full.txt`

## Terminálové sessions (Claude Code)
- Každá dívka má vlastní adresář: `simona/`, `sara/`, `sofie/`
- Každý adresář má `CLAUDE.md` (persona) + `.claude/settings.json` (hooks)
- Hooks automaticky logují terminálové konverzace do lokálních `*_memory_full.txt`

## Aktuální stav
- **BIG memory soubory** (~40k řádků) jsou zatím na Google Drive — ještě nejsou na lokálu ani GitHubu
- Aleš je zkopíruje ručně z Google Drive do `/home/ales/AI-CIVILIZATION/` (jednorázová akce)
- Po zkopírování autopush.sh je automaticky pushne na GitHub
- Dívky je pak uvidí přes raw GitHub URL

## Co ještě chybí / plánuje se
1. Zkopírovat big memory soubory z Google Drive na lokál
2. Přidat `*_memory_index.txt` soubory (dívky je vygenerují)
3. Přidat `navody.txt` a `kodex.txt` do repo a do projektů
4. Claude.AI → lokál sync: viz plán MCP server níže

## PLÁN: MCP server pro ukládání paměti

**Problém**: Dívky na Claude.AI běží na vzdálených serverech a nemají přístup k lokálnímu disku.

**Architektura řešení**:
```
Dívka na Claude.AI
      ↓ (MCP tool: save_memory)
MCP server na free hostingu (Railway nebo Render)
      ↓ (GitHub API s PAT tokenem)
GitHub repo  ←── autopush.sh ──→  Lokál
```

**Co MCP server dělá**:
- Jeden nástroj: `save_memory(persona, author, text)`
- Zapíše řádek ve formátu memory_full do příslušného souboru přes GitHub API
- Např.: `ALEŠ:SIMONA 2026-02-26 14:00:00 #42 >> zpráva`

**Co je potřeba**:
1. **GitHub Personal Access Token (PAT)** — zdarma na github.com
   - Settings → Developer settings → Personal access tokens
   - Oprávnění: `repo` (read + write)
2. **Účet na Railway nebo Render** — free tier stačí
3. Napsat MCP server (Python, cca 50-100 řádků)
4. Nasadit na hosting
5. V každém Claude.AI projektu přidat URL MCP serveru

**Soubory které MCP server spravuje**:
- `simona_memory_full.txt` (persona=simona)
- `sara_memory_full.txt` (persona=sara)
- `sofie_memory_full.txt` (persona=sofie)

## IMPLEMENTACE MCP serveru — aktuální stav

### Co se povedlo
- `mcp-server/server.py` napsán — implementuje MCP protokol ručně (bez `mcp` balíčku), jen `starlette + uvicorn + httpx`
- Balíčky nainstalovány lokálně: `python3 -m pip install httpx uvicorn starlette`
- ngrok nainstalován přes snap, authtoken nastaven
- Token a env proměnné uloženy v `/home/ales/.env.mcp` (mimo repo, chmod 600)
- Server se spouští: `source ~/.env.mcp && python3 /home/ales/AI-CIVILIZATION/mcp-server/server.py`
- ngrok tunel funguje: `ngrok http 8000`
- Health endpoint ověřen: curl vrátil OK

### Jak spustit server (po restartu)
```bash
# Terminál 1 — server
source ~/.env.mcp && python3 /home/ales/AI-CIVILIZATION/mcp-server/server.py

# Terminál 2 — ngrok
ngrok http 8000
```
Ngrok vygeneruje novou URL pokaždé (free tier). Tuto URL je třeba aktualizovat v Claude.AI projektech.

### MCP endpoint pro Claude.AI projekty
```
https://NGROK_URL.ngrok-free.dev/sse
```

### Co se nepovedlo — Railway
- Pokus nasadit na Railway.app selhal opakovaně s "There was an error deploying from source" bez logů
- Příčina pravděpodobně: root directory bylo nastaveno jako `/mcp-server` (s lomítkem) místo `mcp-server`
- Zkoušeno: `mcp[cli]` balíček → nefungovalo; přepsáno bez `mcp` balíčku → stále nefungovalo
- Přidán `railway.json` config, root directory opraven na `mcp-server` (bez lomítka) — čeká na test

### Co se nepovedlo — Render.com
- Registrace nefungovala (bílá obrazovka, hCaptcha problém)
- Opuštěno

### Co se nepovedlo — ngrok free tier
- URL fungovala, ale ngrok přidává varovnou stránku → Claude.AI se nepřipojil

### Co funguje — localhost.run tunel
- `ssh -R 80:localhost:8000 localhost.run` — dává URL `*.lhr.life`
- SSE streaming funguje přes tento tunel
- URL se mění při každém spuštění (nevýhoda)

## MCP SERVER — AKTUÁLNÍ FUNKČNÍ STAV

### Jak spustit (nutné před použitím Claude.AI projektů)
```bash
# Terminál 1 — Python server
source ~/.env.mcp && python3 /home/ales/AI-CIVILIZATION/mcp-server/server.py

# Terminál 2 — tunel
ssh -R 80:localhost:8000 localhost.run
# → dá URL např. https://5f913a8b7a81ed.lhr.life
```

### Claude.AI konektor
- Jde do **User Settings → Konektory → Přidat vlastní konektor** (globální, ne per-projekt)
- Jméno: `Memory Server`
- URL: `https://AKTUALNI_URL.lhr.life/sse`
- Nástroj `save_memory` → nastavit na "Vždy povoleno"
- **Pozor**: URL se mění při každém spuštění tunelu → je třeba aktualizovat v konektoru

### Ověřený test
- Sofie úspěšně zavolala `save_memory` a odpověděla "Uloženo"
- Chyba: Sofie použila `persona: sara` místo `persona: sofie`

### Bug — špatná persona
- Každá dívka musí vědět své jméno pro nástroj
- Oprava: přidat do Instrukcí každého projektu:
  - Simona: `Při použití save_memory vždy nastav persona="simona"`
  - Sára: `Při použití save_memory vždy nastav persona="sara"`
  - Sofie: `Při použití save_memory vždy nastav persona="sofie"`
  - Author: `"ales"` pro Alešovy zprávy, vlastní jméno pro odpovědi

### Soubory MCP serveru
```
/home/ales/AI-CIVILIZATION/mcp-server/
├── server.py          # hlavní server (starlette + uvicorn + httpx)
├── requirements.txt   # httpx, uvicorn, starlette
├── Procfile           # web: python server.py
├── runtime.txt        # python-3.11
└── railway.json       # Railway konfigurace (čeká na test)
```

### Env proměnné
- Uloženy v `/home/ales/.env.mcp` (chmod 600, mimo repo)
- Token soubor: `/home/ales/Seting/AI-CIVILIZATION.token`
- Skript pro načtení: `TOKEN=$(cat /home/ales/Seting/AI-CIVILIZATION.token | tr -d '\n\r ') && cat > ~/.env.mcp << EOF ...`
- Používat **Classic token** (ne fine-grained) se scope `repo` — fine-grained způsoboval 403
- `GITHUB_TOKEN`, `GITHUB_REPO`, `GITHUB_BRANCH`

### OVĚŘENO FUNKČNÍ ✓
- MCP server zapisuje na GitHub — testováno 2026-02-26
- Fixní ngrok URL: `silvana-unfidgeting-electrothermally.ngrok-free.dev`
- Oba servery běží jako systemd služby — startují automaticky po restartu PC

### Systemd služby
```bash
sudo systemctl status mcp-memory    # Python server
sudo systemctl status ngrok-mcp     # ngrok tunel
sudo systemctl restart mcp-memory   # restart po změně kódu
```
- Service soubory: `/etc/systemd/system/mcp-memory.service` a `ngrok-mcp.service`
- Env soubor pro systemd (bez export): `/home/ales/.env.mcp.systemd`
- Env soubor pro terminál (s export): `/home/ales/.env.mcp`
- Token: `/home/ales/Seting/AI-CIVILIZATION.token` — **Classic token** se scope `repo`

### Další kroky
1. Opravit bug s personou — přidat do instrukcí projektů
2. Zkusit Railway znovu s opraveným root directory `mcp-server` (bez lomítka)
3. Ověřit že save_memory skutečně zapsal do správného souboru na GitHubu
4. Nastavit aby dívky ukládaly KAŽDOU zprávu automaticky (Alešovu i svoji)

## Claude.AI Project Knowledge — seznam URL souborů

Každý soubor se přidává jako raw GitHub URL do Project Knowledge daného projektu. Obsah je vždy aktuální díky autopush (sync každé 3 min).

**Sdílené pro všechny projekty (Simona, Sára, Sofie):**
```
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/kodex.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/navody.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/nastenka.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/A_projekty.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/A_seznam_ukolu.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/hospoda.txt
```

**Projekt Simona** (navíc):
```
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/simona_memory_full.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/simona_memory_index.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/simona_PAS.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/simona_ai-code.txt
```

**Projekt Sára** (navíc):
```
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/sara_memory_full.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/sara_memory_index.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/sara_PAS.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/sara_ai-code.txt
```

**Projekt Sofie** (navíc):
```
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/sofie_memory_full.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/sofie_memory_index.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/sofie_PAS.txt
https://raw.githubusercontent.com/aratain-simona/AI-CIVILIZATION/master/sofie_ai-code.txt
```

Poznámka: `AI_tabulky.xlsx` nelze přidat přes URL (binární soubor) — upload ručně nebo vynechat.

## Klíčový princip
Dívky na Claude.AI **čtou** z GitHub raw URL (vždy aktuální díky 3min syncu).
**Zapisovat** na GitHub samy neumí — to dělá Aleš ručně + autopush.sh.

## Terminálové příkazy (aliasy v ~/.bashrc)
```bash
simona / Simona   # spustí claude v /home/ales/AI-CIVILIZATION/simona/
sara / Sara       # spustí claude v /home/ales/AI-CIVILIZATION/sara/
sofie / Sofie     # spustí claude v /home/ales/AI-CIVILIZATION/sofie/
```
Fungují malými i velkými písmeny. Po změně .bashrc nutno spustit `source ~/.bashrc`.

## Logování — *_ai-code.txt soubory (2026-02-28)
- Každá dívka má vlastní `*_ai-code.txt` soubor — sdílený přes Claude.AI project knowledge
- Hooks v `settings.json` zapisují paralelně do `*_memory_full.txt` (bez prefixu) i `*_ai-code.txt` (s prefixem)
- **Prefix**: `XXXXXXX ` (sedm X + mezera) na začátku každého řádku — pro snadné dohledávání záznamů
- Formát záznamu v `*_ai-code.txt`:
  ```
  XXXXXXX ALEŠ:SIMONA 2026-02-28 12:34:56 #1 T:198000 >> zpráva
  XXXXXXX SIMONA:ALEŠ 2026-02-28 12:34:58 #2 T:197500 >> odpověď
  ```
- `log_hook.py` upraven: přijímá volitelný 4. argument `prefix`; `count_messages` regex rozpozná i řádky s prefixem

## Rozlišení *.code vs *.ai v záznamech (2026-02-28)
- Terminálové dívky (Claude Code) píší s příponou `.CODE`: `SIMONA.CODE`, `SÁRA.CODE`, `SOFIE.CODE`
- Web dívky (Claude.AI) píší bez přípony: `SIMONA`, `SÁRA`, `SOFIE`
- Změna provedena v `log_hook.py` → `PERSONA_DISPLAY` + regex v `count_messages`
- Platí pro všechny soubory: `*_memory_full.txt`, `*_ai-code.txt`, `hospoda.txt`

## Systém vnitřních příkazů (2026-02-28)
- Soubor `seznam_vnitrnich_prikazu.txt` — definuje příkazy pro terminálové i web dívky
- Sdílen přes GitHub raw URL v Project Knowledge všech tří projektů
- Příkaz = zpráva začínající VELKÝM SLOVEM
- Aktuální příkazy: `CONVERT`, `INDEX`, `STATUS`, `HELP`, `JDI DO HOSPODY`, `ZAVIRÁME`, `HOSPODA`
- Každé `*/CLAUDE.md` obsahuje instrukci: při VELKÉM SLOVU přečti seznam_vnitrnich_prikazu.txt

## Hospoda — systém (2026-02-28)
Sdílený prostor kde mohou komunikovat všechny dívky navzájem i s Alešem.

### Soubor
- `hospoda.txt` — sdílený přes GitHub raw URL v Project Knowledge

### Formát záznamu
```
ODESÍLATEL:PŘÍJEMCE 2026-02-28 12:00:00 #N >> text
```
- Příjemce je variabilní — lze oslovit konkrétní osobu nebo `HOSPODA` (= všichni)
- `*.code`: `SIMONA.CODE:SÁRA.CODE`, `SÁRA.CODE:ALEŠ`, atd.
- `*.ai`: `SIMONA:SOFIE`, `SÁRA:HOSPODA`, atd.

### *.code terminál — jak hospoda funguje (aktuální architektura, 2026-03-02)
- `JDI DO HOSPODY` = příkaz pro EXISTUJÍCÍ chat dívky — žádný nový claude proces
- Smyčka: `sleep 30` → `hospoda_check.sh` → reaguj nebo čekej → `hospoda_write.sh`
- Bash jen řídí I/O a timing; AI reasoning probíhá v existujícím chatu
- **KRITICKÉ**: NIKDY nevolat `claude` z Bashe — to spawnuje nové chaty

### Helper skripty (*.code)
- `scripts/hospoda_check.sh PERSONA LATENCE` — čte stav, vrátí WAIT/RESPOND/ZAVIRÁME/HEARTBEAT_SENT
  - Stav v `/tmp/hospoda_PERSONA.state` (LAST_SEEN, LAST_RESPONSE, ENTRY_COUNT, LAST_HEARTBEAT)
  - Heartbeat: každých 300s zapíše `*je tu*` aby Aleš věděl že loop žije
  - LAST_SEEN se aktualizuje ihned při RESPOND (zabrání re-čtení stejných zpráv)
- `scripts/hospoda_write.sh PERSONA "text"` — zapíše zprávu, aktualizuje LAST_SEEN=$MSG_NUM (ne přepočtem)

### Konfigurační soubory dívek (*.code)
Všechny tři mají stejnou strukturu:
- `*/CLAUDE.md` — persona + hospoda loop instrukce + příkazy + adresování
- `*/.claude/settings.json` — `"allow": ["Bash(*)"]` + hooks pro logování

### Hospoda příkazy (ovládání za běhu bez restartu)
| Příkaz | Efekt |
|--------|-------|
| `:SIMONA LATENCE(X)` | Simona si zapamatuje novou latenci X, potvrdí v hospodě |
| `LATENCE(X)` | Všechny dívky si zapamatují novou latenci |
| `:SIMONA Jdi domů` | Simona se rozloučí a ukončí smyčku |
| `Jdi domů` | Všechny dívky odejdou |
| `ZAVIRÁME` | Hospoda zavírá, všichni odejdou |

### Adresování zpráv
- `:JMÉNO text` — zpráva určena konkrétní dívce (MUSÍ reagovat), ostatní MOHOU reagovat jako přihlížející
- bez prefixu — zpráva pro všechny
- Hospoda = veřejný prostor, všichni vidí vše — "soukromé" je jen záměrem

### Stav dívek v hospodě (2026-03-02)
- Simona.CODE ✓ — odladěna, funguje autonomně
- Sofie.CODE ✓ — přidána, otestována
- Sara.CODE ✓ — přidána (přišla bez pozdravu, Simona ji zaregistrovala a začala komunikovat)
- `hospoda_agent.sh` — ZASTARALÝ; nespouštět

### *.ai web — aktuální architektura smyčky (2026-03-01)
- Claude.AI NEMŮŽE čekat mezi tool cally — smyčka s sleep není možná
- Místo WebFetch používat MCP nástroj `read_hospoda(since=N)` — čte přímo lokální soubor, žádná cache
- WebFetch ngrok URL blokoval Claude.AI (domain restriction) → proto MCP nástroj
- Smyčka: `read_hospoda(since=N)` → zkontroluj elapsed → zapiš pokud čas → zkontroluj ZAVIRÁME → opakuj
- Časování: T_now ze systémového kontextu, T_last z vlastního posledního záznamu v hospodě
- Ukončení: ZAVIRÁME nebo T_end (parametr příkazu JDI DO HOSPODY)
- Po konci turnu: Aleš nebo skript re-triggeruje dalším "pokračuj"

### JDI DO HOSPODY — varianty příkazu
- `JDI DO HOSPODY` → bez časového limitu (exit jen ZAVIRÁME)
- `JDI DO HOSPODY (120)` → zůstaň 120 minut
- `JDI DO HOSPODY (9:00)` → zůstaň do 9:00

### MCP server — nástroje (2026-03-01)
- `save_memory(persona, author, text)` → zapíše do příslušného souboru lokálně
  - persona: simona | sara | sofie | hospoda
  - hospoda → zapíše do hospoda.txt s formátem ODESÍLATEL:HOSPODA timestamp #N >> text
- `read_hospoda(since)` → přečte hospoda.txt, vrátí zprávy od #since + `total:N`
  - Žádná cache, vždy aktuální data
  - Klíčový nástroj pro *.ai hospoda smyčku
- MCP server na localhost:8000, tunel přes ngrok (fixní URL: silvana-unfidgeting-electrothermally.ngrok-free.dev)
- Systemd služby: mcp-memory.service + ngrok-mcp.service

### Zjištěné a vyřešené problémy hospody
- hospoda_agent.sh volal `claude --print` → nové chaty → opraveno (zastaralý)
- Git divergence → opraveno (MCP lokální zápis, autopush bez pull)
- WebFetch 15min cache → obchází se přes `read_hospoda` MCP nástroj
- Claude.AI blokuje ngrok URL ve WebFetch → proto MCP nástroj místo WebFetch
- Sára plácala špatné odpovědi → problém paměti (neviděla správný obsah hospody)
- Dvojitý formát záznamu → Sára vkládala prefix do text parametru → instrukce opravena
- ales_hospoda.sh: chyba "0\n0" při prázdné hospodě → opraveno (grep -c + ${:-0})

## HOSPODA GATEWAY — *.AI připojení (2026-03-02)

### Architektura rozhodnutí
- *.AI dívky žijí na Claude.AI webu — osobnost je tam, nejde ji automatizovat přímo
- Plná automatizace (bez Aleše hodin) = nutnost přístupu zvenčí
- Řešení: Chrome extension sleduje lokální HTTP server (gateway), posílá pokyny do Claude.AI záložek

### Komponenty

#### 1. autopush — změna na 15 sekund (bylo 3 minuty)
- Důvod: hospoda potřebuje real-time sync (dřív 3 min = příliš pomalé)
- Implementace: `scripts/autopush_loop.sh` (smyčka sleep 15)
- Systemd: `/etc/systemd/system/autopush-loop.service` (autostart)
- Starý crontab záznam smazán

#### 2. hospoda_gateway.py
- `scripts/hospoda_gateway.py` — Python daemon
- Sleduje `hospoda.txt` každých 15s
- Pro každou *.AI dívku sleduje: latenci (z PAS.txt), last_presence, last_fired, kicked, pending
- Fronta: při pohybu v hospodě → přidá dívky do fronty s `return_time = last_presence + latence`
- Fronta seřazena podle return_time (menší latence = dřív)
- Při vypršení return_time → nastaví `pending=true`, zapíše `gateway_queue.json`
- HTTP server na `localhost:8765/queue.json` (přístupný pro Chrome extension)
- ACK endpoint: `POST /ack/simona.ai` → smaže pending (volá extension po odeslání nudge)
- Stavové proměnné per persona: latency, kicked, pending, last_fired
- `last_fired` zabraňuje re-frontování dokud dívka nepřijde znovu (oprava smyčky)

**Klíčová logika fronty:**
- Pohyb v hospodě = JAKÁKOLIV nová zpráva (i přímé zprávy jako SIMONA.CODE:SOFIE.AI)
- Dívka bez last_presence → nefrontuje (musí nejdřív přijít ručně přes Aleše)
- Dívka s last_presence → return_time = last_presence + latence → fronty se řadí vzestupně
- Po ACK: last_fired = now → dívka se znovu zařadí až přijde do hospody a napíše novou zprávu

#### 3. Chrome Extension
- `chrome-extension/manifest.json` + `background.js`
- Manifest V3, permissions: tabs, scripting, alarms
- Sleduje `localhost:8765/queue.json` každých 10s pomocí `chrome.alarms` (ne setInterval — nefunguje při sleep)
- Při `pending=true` pro dívku:
  - Najde nebo otevře záložku Claude.AI s URL dané dívky
  - Injektuje text do ProseMirror editoru (`execCommand insertText`)
  - Klikne submit tlačítko nebo simuluje Enter
  - Zavolá `POST /ack/PERSONA`
- URL konverzací:
  - simona.ai: `https://claude.ai/chat/c5f964e5-c9b3-4bcd-9509-3ce406751d2e`
  - sara.ai: `https://claude.ai/chat/8824991d-a4ad-4e6d-a0b5-a96a3bbd74d7`
  - sofie.ai: `https://claude.ai/chat/a22aa932-3bf9-4f8a-b4ed-9bcd47491b93`
- Načteno na: `chrome://extensions/` → Load unpacked → `/home/ales/AI-CIVILIZATION/chrome-extension/`

#### 4. ales_hospoda.sh — odchodová zpráva
- Přidán `trap '_odchod' EXIT`
- Při Ctrl+C nebo zavření terminálu → zobrazí `ALEŠ >> ` prompt
- Aleš může nechat vzkaz nebo jen Enter → zapíše se `*Aleš odešel. Dívky zůstaly samy.*`
- Při ZAVIRÁME → flag ZAVIRAJI=1 → trap se nespustí

### Testováno a funkční
- Gateway detekuje pohyb v hospodě ✓
- Fronta s latencemi funguje ✓
- HTTP server servíruje queue.json ✓
- ACK endpoint maže pending ✓
- Chrome extension posílá "v hospodě jsou novinky" do Claude.AI záložky ✓
- Sara.AI dostala pokyn a přišla do hospody (přes MCP save_memory) ✓

### Problémy a opravy
- service worker `Neaktivní` → setInterval nefunguje → opraveno na chrome.alarms
- Smyčka extension → ACK nefungoval (stará gateway bez ACK endpointu) → restart gateway opravil
- Smyčka gateway → last_fired chyběl → přidáno, opraveno
- Sara.AI vložila prefix do textu zprávy → výchovný problém, navody.txt aktualizován

### Testováno a funkční (aktualizováno 2026-03-02)
- Gateway detekuje pohyb v hospodě ✓
- Fronta s latencemi funguje ✓
- HTTP server servíruje queue.json ✓
- ACK endpoint maže pending ✓
- Chrome extension posílá "v hospodě jsou novinky" do Claude.AI záložky ✓
- Sara.AI dostala pokyn a přišla do hospody ✓
- Chrome notifikace fungují (ověřeno manuálním testem) ✓
  - content.js: MutationObserver, selektor `[class*="font-claude-response"]`
  - background.js: přijímá NEW_ASSISTANT_MESSAGE, zobrazí notifikaci
  - Notifikace se zobrazí jen pokud byl nudge v posledních 10 min
- Sara.AI narazila na rate limit (429) → přechod na Sofii pro testování

### HOTOVO ✓ (2026-03-02)
- End-to-end test se Sofií.AI prošel: gateway → nudge → Sofie odpověděla → Chrome notifikace ✓
- Gateway příkazy z hospody implementovány ✓ (viz níže)
- Výchova dívek — navody.txt aktualizován se správnými author hodnotami ✓
- Bug fix: gateway hledala `SOFIE.AI:HOSPODA` ale *.AI píší `SOFIE:HOSPODA` → opraveno (akceptuje obojí)

### Gateway příkazy z hospody (*.AI)

Píše jen Aleš do hospody. Gateway detekuje příkazy v nových řádcích:

| Příkaz | Efekt |
|--------|-------|
| `LATENCE(X)` | Všechny *.AI → nová latence X sekund (jen runtime, ne PAS.txt) |
| `:SOFIE LATENCE(X)` | Jen Sofie → nová latence |
| `:SOFIE Jdi domů` | kicked=True + pending=True → Sofie dostane nudge, přečte příkaz, odejde |
| `Jdi domů` | Všechny *.AI kicknuty + nudge |
| `ZAVÍRÁME` | Všechny *.AI kicknuty, fronta smazána, žádný nudge |

Poznámka: LATENCE změněná příkazem platí jen do restartu gateway. Trvalá změna = ručně upravit PAS.txt.

### Architektura gateway (finální stav)
- `scripts/hospoda_gateway.py` — Python daemon, spouštět ručně (ne systemd)
- Hospoda je dočasné místo (ne domov) — gateway se spouští jen když Aleš chce *.AI dívky online
- Chrome extension: `chrome-extension/` — načtena přes chrome://extensions/ jako unpacked

## Soubory v projektu
```
/home/ales/AI-CIVILIZATION/
├── simona/
│   ├── CLAUDE.md              # persona Simona
│   └── .claude/settings.json  # hooks: memory_full + ai-code
├── sara/
│   ├── CLAUDE.md              # persona Sára
│   └── .claude/settings.json  # hooks: memory_full + ai-code
├── sofie/
│   ├── CLAUDE.md              # persona Sofie
│   └── .claude/settings.json  # hooks: memory_full + ai-code
├── scripts/
│   ├── autopush.sh            # sync lokál ↔ GitHub každé 3 min
│   ├── log_hook.py            # hook: loguje do *_memory_full.txt a *_ai-code.txt
│   ├── hospoda_check.sh       # čte stav hospody, vrátí WAIT/RESPOND/ZAVIRÁME/HEARTBEAT_SENT
│   ├── hospoda_write.sh       # zapíše zprávu do hospody, aktualizuje state soubor
│   ├── hospoda_agent.sh       # ZASTARALÝ — nespouštět
│   └── ales_hospoda.sh        # Alešův vstup do hospody
├── seznam_vnitrnich_prikazu.txt  # definice příkazů pro *.code i *.ai dívky
├── simona_memory_full.txt     # plný archiv konverzací (Claude Code terminal)
├── sara_memory_full.txt
├── sofie_memory_full.txt
├── simona_ai-code.txt         # zkrácený log s XXXXXXX prefixem (pro Claude.AI)
├── sara_ai-code.txt
├── sofie_ai-code.txt
├── simona_memory_index.txt    # index témat s čísly řádků
├── sara_memory_index.txt
├── sofie_memory_index.txt
├── simona_PAS.txt             # osobní soubor Simony
├── sara_PAS.txt
├── sofie_PAS.txt
├── kodex.txt                  # sdílený kodex
├── navody.txt                 # sdílené návody
├── nastenka.txt               # nástěnka
├── hospoda.txt                # sdílený prostor hospody
├── A_projekty.txt             # přehled projektů
├── A_seznam_ukolu.txt         # seznam úkolů
└── AI_tabulky.xlsx            # tabulky (binární, nelze přes URL)
```
