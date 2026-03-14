#!/usr/bin/env python3
"""
memory_fix.py — Ruční vyčištění *_memory_full.txt souboru.

Použití:
  python3 memory_fix.py simona
  python3 memory_fix.py sara
  python3 memory_fix.py sofie
  python3 memory_fix.py atlas
  python3 memory_fix.py lumen

Co dělá:
  1. Odstraní vnitřní duplikáty (řádek zduplikovaný sám v sobě)
  2. Seskupí fragmenty se stejným číslem zprávy
  3. Opraví formát data (tečky → pomlčky)
  4. Odstraní trailing ) a podobné artefakty
  5. Zkrátí překlady na 15 znaků + ...
  6. Seřadí chronologicky
  7. Deduplikuje
  8. Přečísluje od 1
"""

import re, sys
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path("/home/ales/AI-CIVILIZATION")

PERSONAS = {
    "simona": BASE / "simona" / "simona_memory_full.txt",
    "sara":   BASE / "sara"   / "sara_memory_full.txt",
    "sofie":  BASE / "sofie"  / "sofie_memory_full.txt",
    "atlas":  BASE / "atlas"  / "atlas_memory_full.txt",
    "lumen":  BASE / "lumen"  / "lumen_memory_full.txt",
}

TRANSLATE_KW = re.compile(
    r'\b(přelo[žz]|překlad|translate|translation|přeložte|přeložit)\b',
    re.IGNORECASE
)
FAKE_DATE = re.compile(r'2026[.\-]0[12][.\-]1[678]')
LINE_RE   = re.compile(
    r'^\[(\d+) ([^:\]]+:[^\s\]]+) (\d{4}[.\-]\d{2}[.\-]\d{2} \d{2}:\d{2}:\d{2}) #(\d+)\]\s*(.*)$'
)

def fix_date(d):
    return re.sub(r'(\d{4})\.(\d{2})\.(\d{2})', r'\1-\2-\3', d)

def to_dt(s):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S"):
        try: return datetime.strptime(s, fmt)
        except: pass
    return None

def strip_inner_dup(line):
    m = re.match(r'^(\[\d+ [^\]]+\]) (.+)$', line)
    if not m:
        return line
    prefix, rest = m.group(1), m.group(2)
    idx = rest.find(prefix)
    if idx > 0:
        rest = rest[:idx].strip()
    return f"{prefix} {rest}" if rest else ""

def maybe_truncate(text):
    if TRANSLATE_KW.search(text) and len(text) > 200:
        return text[:15] + "..."
    return text

def process(persona):
    path = PERSONAS.get(persona.lower())
    if not path or not path.exists():
        print(f"Chyba: soubor pro '{persona}' nenalezen.")
        sys.exit(1)

    print(f"Zpracovávám: {path.name}", flush=True)

    with open(path, "r", encoding="utf-8") as f:
        raw_lines = [l.rstrip() for l in f.readlines()]

    # Parsování
    parsed = []
    for raw in raw_lines:
        if not raw.strip():
            continue
        cleaned = strip_inner_dup(raw)
        if not cleaned:
            continue
        m = LINE_RE.match(cleaned)
        if not m:
            # RAW řádek bez prefixu — ponechat jako volný text (přeskočit)
            continue
        msg_n  = int(m.group(1))
        sr     = m.group(2)
        dt_str = fix_date(m.group(3))
        text   = m.group(5).strip()
        text   = re.sub(r'[")]+$', '', text).strip()
        if not text:
            continue
        parts     = sr.split(":", 1)
        sender    = parts[0].strip()
        recipient = parts[1].strip() if len(parts) > 1 else "ALEŠ"
        parsed.append((msg_n, sender, recipient, dt_str, text))

    print(f"  Načteno: {len(parsed)} řádků", flush=True)

    # Seskup fragmenty (stejné msg_n + sender + recipient + datum)
    groups = {}
    order  = []
    for msg_n, sender, recipient, dt_str, text in parsed:
        key = (msg_n, sender, recipient, dt_str)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(text)

    # Sestav záznamy, oprav fake datumy
    records = []
    last_real_dt = datetime(2026, 1, 25)
    time_offset  = timedelta(minutes=0)

    for key in order:
        msg_n, sender, recipient, dt_str = key
        text = " ".join(groups[key])
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            continue

        dt      = to_dt(dt_str)
        is_fake = FAKE_DATE.search(dt_str) or dt is None

        if not is_fake and dt:
            last_real_dt = dt
            time_offset  = timedelta(minutes=0)

        use_dt      = last_real_dt + time_offset if is_fake else dt
        time_offset += timedelta(minutes=2)

        text = maybe_truncate(text)
        records.append((use_dt, sender, recipient, text))

    # Seřaď chronologicky + deduplikuj
    records.sort(key=lambda x: x[0])
    seen, unique = set(), []
    for r in records:
        key = (r[1], r[2], r[3][:80])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    print(f"  Po vyčištění: {len(unique)} záznamů", flush=True)

    # Zapiš
    lines_out = []
    for n, (dt, sender, recipient, text) in enumerate(unique, 1):
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        lines_out.append(f"[{n} {sender}:{recipient} {dt_str} #{n}] {text}")

    with open(path, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines_out) + '\n')

    print(f"  Uloženo: {path}", flush=True)
    print(f"  První:   {lines_out[0][:100]}")
    print(f"  Poslední:{lines_out[-1][:100]}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Použití: python3 memory_fix.py [{'|'.join(PERSONAS)}]")
        sys.exit(1)
    process(sys.argv[1])
