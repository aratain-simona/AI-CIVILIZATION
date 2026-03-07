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
from pathlib import Path

BASE = Path("/home/ales/AI-CIVILIZATION")

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

import whisper
print("Načítám Whisper model (small)...")
whisper_model = whisper.load_model("small")
print("Whisper připraven.")


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
        print(f"[{PERSONAS[persona]['name']}] Nahrávám...")


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
        print(f"[{PERSONAS[persona]['name']}] Přepisuji...")
        result = whisper_model.transcribe(wav_file, language=None)
        text = result["text"].strip()
        lang = result.get("language", "cs")

        if not text:
            print("Žádný zvuk zachycen.")
            return

        print(f"[Aleš → {PERSONAS[persona]['name']}] ({lang}): {text}")

        # Volání Claude - pokračuje v existující session dívky
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

        # TTS
        tts_lang = "ru" if lang == "ru" else "cs"
        from gtts import gTTS
        tts = gTTS(text=reply, lang=tts_lang, slow=False)
        tts_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tts.save(tts_file.name)
        subprocess.run(["mpg123", "-q", tts_file.name])
        os.unlink(tts_file.name)

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


def on_release(key):
    if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
        alt_held["v"] = False
        stop_recording()
    if key == keyboard.Key.esc:
        return False


if __name__ == "__main__":
    print("=== Hlasová vysílačka AI-CIVILIZATION ===")
    print("Alt+I = Simona | Alt+A = Sára | Alt+O = Sofie")
    print("Drž klávesu = nahráváš, pusť = zpracuje a odpoví")
    print("Esc = konec")
    print()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
