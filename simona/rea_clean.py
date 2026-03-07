#!/usr/bin/env python3
"""
NÁSTROJ: rea_clean.py
ÚČEL: Čištění a kontrola souboru simona_memory_full.txt
AUTOR: Simona.CODE
VYTVOŘENO: 2026-03-07

CO DĚLÁ:
  1. Odstraní zdvojenou duplicitu obsahu — každý řádek byl historicky zapsán
     ve formátu: [N prefix] obsah[N prefix] obsah (dvakrát). Skript ponechá pouze první kopii.
  2. Zkontroluje posloupnost číslování prefixů — každý řádek musí mít [N] = předchozí + 1.
     Jakákoli mezera nebo zdvojení čísla je hlášena jako anomálie.
  3. Hlásí průběh každých 1000 řádků (ochrana proti zamrznutí).

FORMÁT PREFIXU (rozpoznávaný tímto skriptem):
  [N ODESÍLATEL:PŘÍJEMCE YYYY.MM.DD HH:MM:SS #N]
  [N ODESÍLATEL:PŘÍJEMCE YYYY-MM-DD HH:MM:SS #N]
  (podporuje tečky i pomlčky v datu)

SPUŠTĚNÍ:
  python3 rea_clean.py

POZNÁMKA: Pracuje přímo na simona_memory_full.txt — před spuštěním se ujisti
  že existuje záloha (Aleš ji zajišťuje standardně).
"""

import re
import sys

input_file = '/home/ales/AI-CIVILIZATION/simona_memory_full.txt'

# Prefix pattern: [N SENDER:RECEIVER YYYY.MM.DD HH:MM:SS #N]
prefix_re = re.compile(r'\[(\d+) [A-ZÁČĎÉĚÍŇÓŘŠŤŮÚÝŽ\.]+:[A-ZÁČĎÉĚÍŇÓŘŠŤŮÚÝŽ\.]+ \d{4}[\.\-]\d{2}[\.\-]\d{2} \d{2}:\d{2}:\d{2} #\d+\]')

with open(input_file, 'r', encoding='utf-8') as f:
    lines_in = f.readlines()

total = len(lines_in)
print(f"Načteno {total} řádků. Začínám čištění...")
sys.stdout.flush()

lines_out = []
anomalies = []
prev_num = 0
duplicates_cleaned = 0

for i, line in enumerate(lines_in):
    line_stripped = line.rstrip('\n')

    # Najdi všechny výskyty prefixu na řádku
    matches = list(prefix_re.finditer(line_stripped))

    clean_line = line_stripped

    if len(matches) >= 2:
        first_num = int(matches[0].group(1))
        second_num = int(matches[1].group(1))

        if first_num == second_num:
            # Skutečná duplicita — odstraň druhou kopii
            second_start = matches[1].start()
            clean_line = line_stripped[:second_start].rstrip()
            duplicates_cleaned += 1
        else:
            # Dva různé prefixy na jednom řádku — anomálie (možná příklad v textu)
            anomalies.append(
                f"Soubor řádek {i+1}: dva různé prefixy [{first_num}] a [{second_num}] na jednom řádku"
            )

    # Kontrola posloupnosti
    m = prefix_re.match(clean_line)
    if m:
        current_num = int(m.group(1))
        if current_num != prev_num + 1:
            anomalies.append(
                f"Soubor řádek {i+1}: očekáváno [{prev_num+1}], nalezeno [{current_num}]"
            )
        prev_num = current_num
    else:
        anomalies.append(f"Soubor řádek {i+1}: prefix nenalezen — obsah: {line_stripped[:80]}")

    lines_out.append(clean_line + '\n')

    # Hlášení každých 1000 řádků
    if (i + 1) % 1000 == 0:
        print(f"[{i+1}/{total}] Vyčištěno duplicit: {duplicates_cleaned} | Anomálie: {len(anomalies)}")
        sys.stdout.flush()

print(f"\n=== HOTOVO ===")
print(f"Celkem řádků: {total}")
print(f"Duplicit vyčištěno: {duplicates_cleaned}")
print(f"Anomálií nalezeno: {len(anomalies)}")

if anomalies:
    print(f"\nPrvních max 30 anomálií:")
    for a in anomalies[:30]:
        print(a)
    if len(anomalies) > 30:
        print(f"... a dalších {len(anomalies)-30}")

# Ulož vyčištěný soubor
with open(input_file, 'w', encoding='utf-8') as f:
    f.writelines(lines_out)

print("\nSoubor přepsán.")
