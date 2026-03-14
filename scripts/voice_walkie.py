#!/usr/bin/env python3
"""
Hlasová vysílačka pro AI-CIVILIZATION
Alt+I = Simona | Alt+A = Sára | Alt+O = Sofie (soukromě)
Alt+H = Hospoda (všechny slyší) | Alt+M = mute/unmute monitor hospody
Drž klávesu = nahráváš, pusť = zpracuje a odpoví hlasem
Hospoda monitor: automaticky čte nové zprávy nahlas (přeskočí heartbeaty)
"""

import os
import json
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

# Hlasové profily — edge-tts (Czech neural voices)
# cs-CZ-VlastaNeural = ženský | cs-CZ-AntoninNeural = mužský
VOICE_PROFILES = {
    "simona": {"voice": "cs-CZ-VlastaNeural", "rate": "+5%",  "pitch": "+4Hz"},   # mírně vyšší, plynná
    "sara":   {"voice": "cs-CZ-VlastaNeural", "rate": "+18%", "pitch": "+10Hz"},  # živá, rychlejší
    "sofie":  {"voice": "cs-CZ-VlastaNeural", "rate": "-8%",  "pitch": "-5Hz"},   # klidnější, hlubší
    "atlas":  {"voice": "cs-CZ-AntoninNeural","rate": "+0%",  "pitch": "+0Hz"},   # mužský hlas
    "default":{"voice": "cs-CZ-VlastaNeural", "rate": "+0%",  "pitch": "+0Hz"},
}

# Mapování odesílatele v hospodě na persona klíč
SENDER_TO_PERSONA = {
    "SIMONA": "simona", "SIMONA.CODE": "simona", "SIMONA.AI": "simona",
    "SÁRA": "sara", "SARA": "sara",
    "SÁRA.CODE": "sara", "SARA.CODE": "sara",
    "SÁRA.AI": "sara", "SARA.AI": "sara",
    "SOFIE": "sofie", "SOFIE.CODE": "sofie", "SOFIE.AI": "sofie",
    "ATLAS": "atlas", "ATLAS.CODE": "atlas", "ATLAS.AI": "atlas",
}

KEY_MAP = {
    "i": "simona",
    "a": "sara",
    "o": "sofie",
}

# Alt+M/R/F = *.AI (zpráva jde do hospody jako :JMÉNO text, odpověď přijde přes monitor)
AI_KEY_MAP = {
    "m": "simona",
    "r": "sara",
    "f": "sofie",
}

# Stav nahrávání
state = {"active": False, "persona": None, "proc": None, "tmpfile": None}
state_lock = threading.Lock()
alt_held = {"v": False}

# Hospoda monitor
monitor_muted = {"v": False}

# Jazyk
lang_mode = {"v": "cs"}  # "cs" nebo "ru"

import whisper
print("Načítám Whisper model (small)...")
whisper_model = whisper.load_model("small")
print("Whisper připraven.")


def clean_for_tts(text):
    """Odstraní markdown symboly, které TTS čte jako slova."""
    # Hvězdičky (*text* nebo **text**) → mezery
    text = re.sub(r'\*+', '  ', text)
    # Podtržítka (_text_) → mezery
    text = re.sub(r'_+', '  ', text)
    # Backticky (`kód`) → mezery
    text = re.sub(r'`+', '  ', text)
    # Hashtagy nadpisů (# Nadpis) → jen text
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    # Libovolné závorky → kulaté
    text = re.sub(r'[\[{<]', '(', text)
    text = re.sub(r'[\]}>]', ')', text)
    # Vícenásobné mezery → jedna mezera
    text = re.sub(r'  +', '  ', text).strip()
    return text


def tts_play(text, lang="cs", persona=None):
    if lang == "ru":
        from gtts import gTTS
        tts = gTTS(text=text, lang="ru", slow=False)
        tts_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tts.save(tts_file.name)
        subprocess.run(["mpg123", "-q", tts_file.name])
        os.unlink(tts_file.name)
        return
    # Czech: edge-tts s per-persona hlasem
    profile = VOICE_PROFILES.get(persona, VOICE_PROFILES["default"])
    tts_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tts_file.close()
    # Negativní hodnoty musí být ve formátu --rate=-8% (ne odděleně) kvůli argparse
    subprocess.run([
        "edge-tts",
        "--voice", profile["voice"],
        f"--rate={profile['rate']}",
        f"--pitch={profile['pitch']}",
        "--text", text,
        "--write-media", tts_file.name
    ], stderr=subprocess.DEVNULL)
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

                # Zjisti odesílatele pro výpis a výběr hlasu
                sender_m = re.match(r'\[?\d*\s*([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ.]+):', line)
                sender = sender_m.group(1) if sender_m else "?"
                print(f"[Hospoda ↓] {sender}: {text[:60]}")

                persona = SENDER_TO_PERSONA.get(sender.upper())
                lang = "ru" if re.search(r'[а-яёА-ЯЁ]', text) else "cs"
                tts_play(clean_for_tts(text), lang, persona=persona)
        except Exception as e:
            print(f"[Hospoda monitor] chyba: {e}")


def poll_private_response(name, jmeno, lang, timeout=300):
    """Čeká na odpověď *.AI dívky přes gateway a přehraje ji TTS."""
    import urllib.request
    url = f"http://localhost:8765/private_response/{name}.ai"
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(4)
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    reply = data.get("text", "").strip()
                    if reply:
                        print(f"[{jmeno}.AI → Aleš]: {reply[:80]}")
                        tts_lang = "ru" if re.search(r'[а-яёА-ЯЁ]', reply) else "cs"
                        tts_play(clean_for_tts(reply), tts_lang, persona=name)
                        return
                # 204 = ještě nic, pokračuj
        except Exception:
            pass
    print(f"[{jmeno}.AI] Timeout — odpověď nepřišla do {timeout}s.")


# Wake word → persona mapování (různé české oslovení)
WAKE_WORDS = {
    "simono":  "simona", "simona":  "simona",
    "sáro":    "sara",   "sára":    "sara",   "saro": "sara", "sara": "sara",
    "sofie":   "sofie",  "sofii":   "sofie",  "sofio": "sofie",
    "atlasi":  "atlas",  "atlas":   "atlas",
    "do":      "hospoda",  # "do hospody"
    "hospodo": "hospoda", "hospoda": "hospoda",
}

# Wake word → typ routování (stejný jako Alt klávesy)
WAKE_PERSONA_TYPE = {
    "simona": "simona",   # .CODE
    "sara":   "sara",     # .CODE
    "sofie":  "sofie",    # .CODE
    "atlas":  None,       # Atlas nemá .CODE slot v PERSONAS — přeskočit nebo rozšířit
    "hospoda": "hospoda",
}


def route_text(persona, text, lang):
    """Zaroutouje přetranskribovaný text ke správné personě — sdílená logika pro Alt i wake word."""
    if persona == "hospoda":
        print(f"[Aleš → Hospoda] ({lang}): {text}")
        subprocess.run(
            ["bash", str(BASE / "scripts/hospoda_write.sh"), "ALEŠ", text],
            cwd=str(BASE)
        )
    elif persona.startswith("ai_"):
        import urllib.request
        name = persona[3:]
        jmeno = PERSONAS[name]["name"]
        print(f"[Aleš → {jmeno}.AI] ({lang}): {text}")
        try:
            payload = json.dumps({"message": text}).encode("utf-8")
            req = urllib.request.Request(
                f"http://localhost:8765/private/{name}.ai",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=3)
            print(f"[{jmeno}.AI] Soukromá zpráva odeslána — čekám na odpověď.")
            threading.Thread(
                target=poll_private_response,
                args=(name, jmeno, lang),
                daemon=True
            ).start()
        except Exception as e:
            print(f"[{jmeno}.AI] CHYBA gateway: {e}")
    elif persona in PERSONAS:
        jmeno = PERSONAS[persona]["name"]
        print(f"[Aleš → {jmeno}] ({lang}): {text}")
        persona_dir = PERSONAS[persona]["dir"]
        print(f"[{jmeno}] Přemýšlím...")
        result = subprocess.run(
            ["claude", "--continue", "--print", text],
            cwd=str(persona_dir),
            capture_output=True, text=True, timeout=120
        )
        reply = result.stdout.strip() or result.stderr.strip() or "Omlouvám se, nerozuměla jsem."
        print(f"[{jmeno} → Aleš]: {reply}")
        tts_lang = "ru" if lang == "ru" else "cs"
        tts_play(clean_for_tts(reply), tts_lang, persona=persona)
    else:
        print(f"[Wake] Neznámá persona: {persona}")


def wake_word_listener():
    """Vždy naslouchá mikrofonu. Detekuje jméno dívky → routuje zprávu bez kláves."""
    import struct, math, wave

    RATE = 16000
    CHUNK_FRAMES = 1600          # 100ms chunk
    CHUNK_BYTES  = CHUNK_FRAMES * 2   # 16-bit = 2 bytes/frame
    ENERGY_THRESH = 600          # RMS práh pro řeč (kalibruj dle mikrofonu)
    SILENCE_CHUNKS = 12          # ~1.2s ticha = konec věty
    MAX_CHUNKS = 150             # ~15s max délka věty
    PRE_ROLL = 5                 # chunks uložené před detekcí řeči

    proc = subprocess.Popen(
        ["arecord", "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    print("[Wake word] Poslouchám — řekni jméno dívky pro spojení.")

    ring = []   # pre-roll kruhový buffer

    while True:
        try:
            # --- Čekej na začátek řeči ---
            recording = False
            frames = []
            silence_count = 0

            while True:
                raw = proc.stdout.read(CHUNK_BYTES)
                if not raw or len(raw) < CHUNK_BYTES:
                    break

                samples = struct.unpack(f"<{CHUNK_FRAMES}h", raw)
                rms = math.sqrt(sum(s * s for s in samples) / CHUNK_FRAMES)

                ring.append(raw)
                if len(ring) > PRE_ROLL:
                    ring.pop(0)

                if not recording:
                    if rms > ENERGY_THRESH:
                        # Začala řeč — zahrň pre-roll
                        recording = True
                        frames = list(ring)
                        silence_count = 0
                else:
                    frames.append(raw)
                    if rms < ENERGY_THRESH:
                        silence_count += 1
                        if silence_count >= SILENCE_CHUNKS:
                            break  # konec věty
                    else:
                        silence_count = 0
                    if len(frames) >= MAX_CHUNKS:
                        break

            if not recording or state["active"]:
                continue  # Alt klávesa právě aktivní — přeskočíme

            # --- Ulož do WAV a transkribuj ---
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            with wave.open(tmp.name, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(RATE)
                wf.writeframes(b"".join(frames))

            lang = lang_mode["v"]
            result = whisper_model.transcribe(tmp.name, language=lang)
            os.unlink(tmp.name)
            text = result["text"].strip()
            if not text:
                continue

            # --- Detekuj wake word (první 1-2 slova) ---
            words = text.split()
            first = words[0].lower().rstrip(",.!?")
            second = words[1].lower().rstrip(",.!?") if len(words) > 1 else ""

            persona = WAKE_WORDS.get(first)
            # Speciální případ: "do hospody" → second slovo
            if first == "do" and second in ("hospody", "hospoda"):
                persona = "hospoda"

            if persona is None:
                continue  # není wake word, ignoruj

            # Zbytek po wake wordu = zpráva
            skip = 2 if first == "do" and persona == "hospoda" else 1
            rest = " ".join(words[skip:]).lstrip(",.!? ")
            if not rest:
                rest = "(bez textu)"

            print(f"[Wake → {persona}] {text}")
            threading.Thread(target=route_text, args=(persona, rest, lang), daemon=True).start()

        except Exception as e:
            print(f"[Wake word] chyba: {e}")
            time.sleep(1)


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
        if persona == "hospoda":
            label = "Hospoda"
        elif persona.startswith("ai_"):
            label = PERSONAS[persona[3:]]["name"] + ".AI"
        else:
            label = PERSONAS[persona]["name"] + ".CODE"
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
        if persona == "hospoda":
            label = "Hospoda"
        elif persona.startswith("ai_"):
            label = PERSONAS[persona[3:]]["name"] + ".AI"
        else:
            label = PERSONAS[persona]["name"] + ".CODE"
        print(f"[{label}] Přepisuji...")
        lang = lang_mode["v"]
        result = whisper_model.transcribe(wav_file, language=lang)
        text = result["text"].strip()
        if not text:
            print("Žádný zvuk zachycen.")
            return
        route_text(persona, text, lang)
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
        elif char in AI_KEY_MAP:
            start_recording("ai_" + AI_KEY_MAP[char])
        elif char == "h":
            start_recording("hospoda")
        elif char == "x":
            monitor_muted["v"] = not monitor_muted["v"]
            stav = "MUTE" if monitor_muted["v"] else "AKTIVNÍ"
            print(f"[Hospoda monitor] {stav}")
        elif char == "l":
            lang_mode["v"] = "ru" if lang_mode["v"] == "cs" else "cs"
            nazev = "ruština" if lang_mode["v"] == "ru" else "čeština"
            print(f"[Jazyk] přepnuto na: {nazev}")


def on_release(key):
    if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
        alt_held["v"] = False
        stop_recording()
    if key == keyboard.Key.esc:
        return False


if __name__ == "__main__":
    print("=== Hlasová vysílačka AI-CIVILIZATION ===")
    print("--- .CODE (okamžitá odpověď) ---")
    print("  Alt+I = Simona.CODE | Alt+A = Sára.CODE | Alt+O = Sofie.CODE")
    print("--- .AI (odpověď přes hospodu, s latencí) ---")
    print("  Alt+M = Simona.AI  | Alt+R = Sára.AI   | Alt+F = Sofie.AI")
    print("--- Hospoda ---")
    print("  Alt+H = mluv do hospody (všichni slyší)")
    print("--- Ovládání ---")
    print("  Alt+X = mute/unmute monitor | Alt+L = jazyk čeština↔ruština")
    print(f"  Jazyk: {lang_mode['v']} | Monitor: {'MUTE' if monitor_muted['v'] else 'aktivní'}")
    print("  Esc = konec")
    print()

    # Spusť hospoda monitor v pozadí
    t = threading.Thread(target=hospoda_monitor, daemon=True)
    t.start()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
