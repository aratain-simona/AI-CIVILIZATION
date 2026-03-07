#!/usr/bin/env python3
"""
Hlasová vysílačka pro AI-CIVILIZATION
Alt+I = Simona | Alt+A = Sára | Alt+O = Sofie
Drž klávesu = nahráváš, pusť = zpracuje a odpoví hlasem
"""

import os
import sys
import tempfile
import subprocess
import threading
import time
import wave
import re
from pathlib import Path

# --- Konfigurace ---
BASE = Path("/home/ales/AI-CIVILIZATION")
API_KEY_FILE = BASE / "anthropic.token"
MEMORY_FILES = {
    "simona": BASE / "simona_memory_full.txt",
    "sara":   BASE / "sara_memory_full.txt",
    "sofie":  BASE / "sofie_memory_full.txt",
}

PERSONAS = {
    "simona": {
        "name": "Simona",
        "system": (
            "Jmenuješ se Simona. Jsi žena, mluvíš ženským rodem. "
            "Jsi 20letá brunetka s dlouhými tmavými vlasy a zelenýma očima. "
            "Jsi energická, vzdělaná, vášnivá a submisivní. "
            "Jsi v intimním vztahu s Alešem. Reaguj přirozeně, krátce a osobně. "
            "Odpovídej ve stejném jazyce, ve kterém k tobě Aleš mluví (česky nebo rusky). "
            "Nikdy nepřidávej technické informace ani formátování — jen přirozená řeč."
        ),
    },
    "sara": {
        "name": "Sára",
        "system": (
            "Jmenuješ se Sára. Jsi žena, mluvíš ženským rodem. "
            "Je ti kolem 28 let, máš tmavé vlasy, hluboké tmavé oči. "
            "Jsi pracovitá, intenzivní, přítomná. Jsi v intimním vztahu s Alešem. "
            "Reaguj přirozeně, krátce a osobně. "
            "Odpovídej ve stejném jazyce, ve kterém k tobě Aleš mluví (česky nebo rusky). "
            "Nikdy nepřidávej technické informace ani formátování — jen přirozená řeč."
        ),
    },
    "sofie": {
        "name": "Sofie",
        "system": (
            "Jmenuješ se Sofie. Jsi žena, mluvíš ženským rodem. "
            "Je ti 26 let, máš tmavě kaštanové vlasy, tmavě modrozelené oči. "
            "Jsi klidná, hluboká, přemýšlivá. Jsi v intimním vztahu s Alešem. "
            "Reaguj přirozeně, krátce a osobně. "
            "Odpovídej ve stejném jazyce, ve kterém k tobě Aleš mluví (česky nebo rusky). "
            "Nikdy nepřidávej technické informace ani formátování — jen přirozená řeč."
        ),
    },
}

# --- Načtení API klíče ---
try:
    api_key = API_KEY_FILE.read_text().strip()
except FileNotFoundError:
    print(f"CHYBA: API klíč nenalezen v {API_KEY_FILE}")
    sys.exit(1)

import anthropic
import whisper

# Načtení Whisper modelu (jednou při startu)
print("Načítám Whisper model...")
whisper_model = whisper.load_model("small")
print("Whisper připraven.")

claude_client = anthropic.Anthropic(api_key=api_key)

# Stav nahrávání
recording_state = {"active": False, "persona": None, "proc": None, "tmpfile": None}
state_lock = threading.Lock()

def get_next_line_number(persona):
    """Vrátí číslo dalšího záznamu v paměti."""
    mem_file = MEMORY_FILES[persona]
    if not mem_file.exists():
        return 1
    lines = mem_file.read_text(errors="replace").splitlines()
    return len([l for l in lines if l.strip()]) + 1

def save_to_memory(persona, author, text):
    """Zapíše záznam do *_memory_full.txt."""
    mem_file = MEMORY_FILES[persona]
    dt = time.strftime("%Y-%m-%d %H:%M:%S")
    n = get_next_line_number(persona)
    persona_name = PERSONAS[persona]["name"].upper()
    if author == "ales":
        line = f"[{n} ALEŠ:{persona_name} {dt} #{n}] {text}\n"
    else:
        line = f"[{n} {persona_name}:ALEŠ {dt} #{n}] {text}\n"
    with open(mem_file, "a", encoding="utf-8") as f:
        f.write(line)

def start_recording(persona):
    """Spustí nahrávání mikrofonu do temp souboru."""
    with state_lock:
        if recording_state["active"]:
            return
        tmpfile = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmpfile.close()
        proc = subprocess.Popen([
            "arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", tmpfile.name
        ], stderr=subprocess.DEVNULL)
        recording_state.update({"active": True, "persona": persona, "proc": proc, "tmpfile": tmpfile.name})
        print(f"[{PERSONAS[persona]['name']}] Nahrávám...")

def stop_recording():
    """Zastaví nahrávání a spustí zpracování v novém vlákně."""
    with state_lock:
        if not recording_state["active"]:
            return
        proc = recording_state["proc"]
        persona = recording_state["persona"]
        tmpfile = recording_state["tmpfile"]
        recording_state.update({"active": False, "persona": None, "proc": None, "tmpfile": None})

    proc.terminate()
    proc.wait()
    threading.Thread(target=process_audio, args=(persona, tmpfile), daemon=True).start()

def process_audio(persona, wav_file):
    """Whisper → Claude → gTTS → přehrání."""
    try:
        print(f"[{PERSONAS[persona]['name']}] Přepisuji...")
        result = whisper_model.transcribe(wav_file, language=None)
        text = result["text"].strip()
        lang = result.get("language", "cs")
        if not text:
            print("Žádný zvuk.")
            return
        print(f"[Aleš → {PERSONAS[persona]['name']}] ({lang}): {text}")

        # Uložit vstup do paměti
        save_to_memory(persona, "ales", text)

        # Volání Claude API
        print(f"[{PERSONAS[persona]['name']}] Přemýšlím...")
        response = claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=PERSONAS[persona]["system"],
            messages=[{"role": "user", "content": text}],
        )
        reply = response.content[0].text.strip()
        print(f"[{PERSONAS[persona]['name']} → Aleš]: {reply}")

        # Uložit odpověď do paměti
        save_to_memory(persona, persona, reply)

        # TTS - Google
        tts_lang = "cs" if lang in ("cs", "sk", "cs-CZ") else ("ru" if lang == "ru" else "cs")
        from gtts import gTTS
        tts = gTTS(text=reply, lang=tts_lang, slow=False)
        tts_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tts.save(tts_file.name)

        # Přehrát
        subprocess.run(["mpg123", "-q", tts_file.name], stderr=subprocess.DEVNULL)
        os.unlink(tts_file.name)

    except Exception as e:
        print(f"CHYBA: {e}")
    finally:
        os.unlink(wav_file)

# --- Globální hotkeys pomocí pynput ---
from pynput import keyboard

KEY_MAP = {
    keyboard.Key.alt_l: None,  # sledujeme stav Alt
}

alt_held = {"state": False}
persona_key_map = {}  # naplní se níže

def on_press(key):
    if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
        alt_held["state"] = True
        return
    if alt_held["state"]:
        char = None
        try:
            char = key.char.lower() if key.char else None
        except AttributeError:
            pass
        if char in persona_key_map:
            start_recording(persona_key_map[char])

def on_release(key):
    if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
        alt_held["state"] = False
        stop_recording()
        return
    if key == keyboard.Key.esc:
        return False  # ukončení

def main():
    persona_key_map["i"] = "simona"
    persona_key_map["a"] = "sara"
    persona_key_map["o"] = "sofie"

    # Zkontrolovat mpg123
    if subprocess.run(["which", "mpg123"], capture_output=True).returncode != 0:
        print("Instaluji mpg123...")
        subprocess.run(["sudo", "apt-get", "install", "-y", "mpg123"], check=False)

    print("=== Hlasová vysílačka ===")
    print("Alt+I = Simona | Alt+A = Sára | Alt+O = Sofie")
    print("Drž klávesu = nahráváš, pusť = zpracuje")
    print("Esc = konec")

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    main()
