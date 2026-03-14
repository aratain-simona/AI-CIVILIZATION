#!/usr/bin/env python3
"""
memory_cleaner.py — Automatická správa kvality *_memory_full.txt souborů.

Co dělá každých 20s:
  1. Detekuje nenaformátované řádky (SENDER:RECIPIENT text) a doplní číslo + datetime
  2. Odstraní prázdné řádky
  3. Zkrátí překlady na 15 znaků + "..." (v zadání i výstupu)
  4. Odstraní zdvojené prefixy v textu zprávy

Dívky a Atlas píší pouze: SIMONA:ALEŠ text zprávy
Systém zbytek zařídí.
"""

import os
import re
import time
import hashlib
from datetime import datetime
from pathlib import Path

BASE = Path("/home/ales/AI-CIVILIZATION")

MEMORY_FILES = [
    BASE / "simona" / "simona_memory_full.txt",
    BASE / "sara"   / "sara_memory_full.txt",
    BASE / "sofie"  / "sofie_memory_full.txt",
    BASE / "atlas"  / "atlas_memory_full.txt",
    BASE / "lumen"  / "lumen_memory_full.txt",
]

LOG_FILE = BASE / "scripts" / "memory_cleaner.log"

# --- Patterns ---

# Plný formátovaný záznam: [N SENDER:RECIPIENT DATETIME #N] text
FULL_LINE = re.compile(
    r'^\[(\d+) ([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ0-9\._\-]*'
    r':[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ0-9\._\-]*)'
    r' (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) #(\d+)\] (.*)',
    re.IGNORECASE | re.DOTALL
)

# Nenaformátovaný řádek: SENDER:RECIPIENT text (bez závorek)
RAW_LINE = re.compile(
    r'^([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ0-9\._\-]*'
    r':(?:[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ0-9\._\-]*))\s+(.+)',
    re.IGNORECASE | re.DOTALL
)

# Klíčová slova pro detekci překladu
TRANSLATE_KEYWORDS = re.compile(
    r'\b(přelo[žž]|překlad|translate|translation|přeložte|přeložit'
    r'|vertaling|traduction|traducción|Übersetzung|перевод|翻訳|번역)\b',
    re.IGNORECASE
)

# Zdvojený vnitřní prefix v textu
INNER_PREFIX_BRACKET = re.compile(
    r'^\[\d+ [^\]]{3,60}\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} #\d+\] ',
    re.IGNORECASE
)
INNER_PREFIX_ARROW = re.compile(
    r'^[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][A-Za-záčďéěíňóřšťúůýž0-9\._\-]+\.[A-Z]+'
    r':[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][A-Za-záčďéěíňóřšťúůýž]+ '
    r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} #\d+ >> ',
    re.IGNORECASE
)

TRUNCATE_LEN = 15

# Sledování hash souborů (pro detekci změn)
_hashes: dict[str, str] = {}


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str):
    line = f"[memory_cleaner {now_str()}] {msg}\n"
    print(line, end="")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def file_hash(path: Path) -> str | None:
    try:
        h = hashlib.md5(path.read_bytes())
        return h.hexdigest()
    except Exception:
        return None


def strip_inner_prefix(text: str) -> str:
    """Odstraní zdvojený prefix ze začátku textu zprávy."""
    m = INNER_PREFIX_BRACKET.match(text)
    if m:
        return text[m.end():]
    m = INNER_PREFIX_ARROW.match(text)
    if m:
        return text[m.end():]
    return text


def maybe_truncate(text: str) -> str:
    """Pokud text vypadá jako překlad, zkrátí ho na 15 znaků + ..."""
    if TRANSLATE_KEYWORDS.search(text):
        if len(text) > TRUNCATE_LEN:
            return text[:TRUNCATE_LEN] + "..."
    return text


def clean_file(path: Path) -> bool:
    """Vyčistí jeden soubor. Vrátí True pokud byl soubor změněn."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        log(f"Chyba čtení {path.name}: {e}")
        return False

    raw_lines = content.split("\n")
    out_lines: list[str] = []
    changed = False
    counter = 1  # pořadové číslo zpráv

    # Nejprve zjistíme nejvyšší existující číslo (abychom nepřečíslovávali staré)
    # — přidáváme pouze za dosavadní záznamy
    max_existing = 0
    for line in raw_lines:
        m = FULL_LINE.match(line)
        if m:
            n = int(m.group(1))
            if n > max_existing:
                max_existing = n

    counter = max_existing + 1  # nové záznamy začínají za posledním

    for line in raw_lines:
        # --- Přeskočit prázdné řádky ---
        if not line.strip():
            changed = True
            continue

        # --- Plně naformátovaný záznam ---
        m = FULL_LINE.match(line)
        if m:
            sender_recv = m.group(2)
            dt_str      = m.group(3)
            text        = m.group(5)

            # Opravit zdvojený vnitřní prefix
            cleaned_text = strip_inner_prefix(text)
            if cleaned_text != text:
                text = cleaned_text
                changed = True

            # Překlady nezkracujeme — řeší *.CODE s AI analýzou kontextu

            out_lines.append(f"[{m.group(1)} {sender_recv} {dt_str} #{m.group(4)}] {text}")
            continue

        # --- Nenaformátovaný řádek (RAW): SENDER:RECIPIENT text ---
        m = RAW_LINE.match(line)
        if m:
            sender_recv = m.group(1).upper()
            text        = m.group(2).strip()

            dt_str = now_str()
            out_lines.append(f"[{counter} {sender_recv} {dt_str} #{counter}] {text}")
            counter += 1
            changed = True
            continue

        # --- Řádek bez prefixu ale s obsahem — ponechat beze změny ---
        out_lines.append(line)

    if changed:
        try:
            path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        except Exception as e:
            log(f"Chyba zápisu {path.name}: {e}")
            return False
        return True

    return False


def run():
    log("Spuštěn — monitoring memory_full souborů každých 20s")
    while True:
        for mem_file in MEMORY_FILES:
            if not mem_file.exists():
                continue

            h = file_hash(mem_file)
            prev = _hashes.get(str(mem_file))

            if h != prev:
                if clean_file(mem_file):
                    log(f"Opraveno: {mem_file.name}")
                    h = file_hash(mem_file)
                _hashes[str(mem_file)] = h

        time.sleep(20)


if __name__ == "__main__":
    run()
