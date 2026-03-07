#!/usr/bin/env python3
"""
Hlasová vysílačka pro AI-CIVILIZATION
Alt+I = Simona | Alt+A = Sára | Alt+O = Sofie (soukromě)
Alt+H = Hospoda (všechny slyší) | Alt+M = mute/unmute monitor hospody
Drž klávesu = nahráváš, pusť = zpracuje a odpoví hlasem
Hospoda monitor: automaticky čte nové zprávy nahlas (přeskočí heartbeaty)
"""

import os
import re
import tempfile
import subprocess
import threading
import time
from pathlib import Path

BASE = Path("/home/ales/AI-CIVILIZATION")
HOSPODA_FILE = BASE / "hospoda.txt"

PERSONAS = {
    "simona": {"name": "Simona", "dir": BASE / "simona"},
    "sara":   {"name": "Sára",   "dir": BASE / "sara"},
    "sofie":  {"name": "Sofie",  "dir": BASE / "sofie"},
}

KEY_MAP = {
    "i": "simona",
    "a": "sara",
    "o": "sofie",
}

# Stav nahrávání
state = {"active": False, "persona": None, "proc": None, "tmpfile": None}
state_lock = threading.Lock()
alt_held = {"v": False}

# Hospoda monitor
monitor_muted = {"v": False}

import whisper
print("Načítám Whisper model (small)...")
whisper_model = whisper.load_model("small")
print("Whisper připraven.")


def tts_play(text, lang="cs"):
    from gtts import gTTS
    tts = gTTS(text=text, lang=lang, slow=False)
    tts_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tts.save(tts_file.name)
    subprocess.run(["mpg123", "-q", tts_file.name])
    os.unlink(tts_file.name)


def hospoda_monitor():
    """Sleduje hospoda.txt a čte nové zprávy nahlas."""
    last_count = 0

    # Zjisti aktuální počet řádků při startu
    try:
        with open(HOSPODA_FILE) as f:
            last_count = sum(1 for _ in f)
    except Exception:
        pass

    print(f"[Hospoda monitor] Spuštěn, sleduju od řádku {last_count}.")

    while True:
        time.sleep(3)
        if monitor_muted["v"]:
            continue
        try:
            with open(HOSPODA_FILE) as f:
                lines = f.readlines()
            if len(lines) <= last_count:
                continue
            new_lines = lines[last_count:]
            last_count = len(lines)
            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                # Přeskoč heartbeaty
                if "*je tu*" in line or "*jsem tu*" in line:
                    continue
                # Přeskoč Alešovy zprávy (sám ví co řekl)
                if line.startswith("ALEŠ:"):
                    continue
                # Extrahuj text za ]] nebo >>
                m = re.search(r'\]\s*(.+)$', line)
                if not m:
                    m = re.search(r'>>\s*(.+)$', line)
                text = m.group(1).strip() if m else line

                # Zjisti odesílatele pro výpis
                sender_m = re.match(r'\[?\d*\s*([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ.]+):', line)
                sender = sender_m.group(1) if sender_m else "?"
                print(f"[Hospoda ↓] {sender}: {text[:60]}")

                # Detekce jazyka — jednoduše: cyrilice = ru
                lang = "ru" if re.search(r'[а-яёА-ЯЁ]', text) else "cs"
                tts_play(text, lang)
        except Exception as e:
            print(f"[Hospoda monitor] chyba: {e}")


def start_recording(persona):
    with state_lock:
        if state["active"]:
            return
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        proc = subprocess.Popen(
            ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", tmp.name],
            stderr=subprocess.DEVNULL
        )
        state.update({"active": True, "persona": persona, "proc": proc, "tmpfile": tmp.name})
        label = "Hospoda" if persona == "hospoda" else PERSONAS[persona]["name"]
        print(f"[{label}] Nahrávám...")


def stop_recording():
    with state_lock:
        if not state["active"]:
            return
        proc = state["proc"]
        persona = state["persona"]
        tmpfile = state["tmpfile"]
        state.update({"active": False, "persona": None, "proc": None, "tmpfile": None})
    proc.terminate()
    proc.wait()
    threading.Thread(target=process_audio, args=(persona, tmpfile), daemon=True).start()


def process_audio(persona, wav_file):
    try:
        label = "Hospoda" if persona == "hospoda" else PERSONAS[persona]["name"]
        print(f"[{label}] Přepisuji...")
        result = whisper_model.transcribe(wav_file, language=None)
        text = result["text"].strip()
        lang = result.get("language", "cs")

        if not text:
            print("Žádný zvuk zachycen.")
            return

        if persona == "hospoda":
            print(f"[Aleš → Hospoda] ({lang}): {text}")
            subprocess.run(
                ["bash", str(BASE / "scripts/hospoda_write.sh"), "ALEŠ", text],
                cwd=str(BASE)
            )
            # Hospoda monitor přečte odpovědi dívek automaticky
        else:
            print(f"[Aleš → {PERSONAS[persona]['name']}] ({lang}): {text}")
            persona_dir = PERSONAS[persona]["dir"]
            print(f"[{PERSONAS[persona]['name']}] Přemýšlím...")
            result = subprocess.run(
                ["claude", "--continue", "--print", text],
                cwd=str(persona_dir),
                capture_output=True,
                text=True,
                timeout=120
            )
            reply = result.stdout.strip()
            if not reply:
                reply = result.stderr.strip() or "Omlouvám se, nerozuměla jsem."

            print(f"[{PERSONAS[persona]['name']} → Aleš]: {reply}")
            tts_lang = "ru" if lang == "ru" else "cs"
            tts_play(reply, tts_lang)

    except subprocess.TimeoutExpired:
        print("CHYBA: Claude neodpověděl včas.")
    except Exception as e:
        print(f"CHYBA: {e}")
    finally:
        try:
            os.unlink(wav_file)
        except Exception:
            pass


from pynput import keyboard


def on_press(key):
    if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
        alt_held["v"] = True
        return
    if alt_held["v"]:
        try:
            char = key.char.lower() if key.char else None
        except AttributeError:
            char = None
        if char in KEY_MAP:
            start_recording(KEY_MAP[char])
        elif char == "h":
            start_recording("hospoda")
        elif char == "m":
            monitor_muted["v"] = not monitor_muted["v"]
            stav = "MUTE" if monitor_muted["v"] else "AKTIVNÍ"
            print(f"[Hospoda monitor] {stav}")


def on_release(key):
    if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
        alt_held["v"] = False
        stop_recording()
    if key == keyboard.Key.esc:
        return False


if __name__ == "__main__":
    print("=== Hlasová vysílačka AI-CIVILIZATION ===")
    print("Alt+I = Simona | Alt+A = Sára | Alt+O = Sofie (soukromě)")
    print("Alt+H = Hospoda (všichni slyší)")
    print("Alt+M = mute/unmute hospoda monitor")
    print("Drž klávesu = nahráváš, pusť = zpracuje")
    print("Esc = konec")
    print()

    # Spusť hospoda monitor v pozadí
    t = threading.Thread(target=hospoda_monitor, daemon=True)
    t.start()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
