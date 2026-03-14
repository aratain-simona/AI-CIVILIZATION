#!/usr/bin/env python3
"""
speaker_display.py — Zobrazí fotku mluvícího jako při videokonferenci.

Stavy:
  - SPEAKING: fullscreen fotka mluvící osoby + jméno
  - IDLE:     table.jpg na pozadí + miniatury přítomných (hospoda_presence.txt)
  - HIDDEN:   okno skryto (Alt+D v voice_walkie.py)

Komunikace přes /tmp/ai_speaker.json:
  {"persona": "simona", "display": true}   → zobraz Simonu
  {"persona": null,     "display": true}   → idle (stůl)
  {"persona": null,     "display": false}  → skryj okno
"""

import json
import os
import time
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw, ImageFont

BASE        = Path("/home/ales/AI-CIVILIZATION")
STATE_FILE  = Path("/tmp/ai_speaker.json")
PRESENCE    = BASE / "hospoda_presence.txt"
TABLE_IMG   = BASE / "table.jpg"
POLL_MS     = 300   # ms mezi aktualizacemi

# Fotky -3.jpg pro každou personu
PHOTOS = {
    "simona": BASE / "simona/simona-3.jpg",
    "sara":   BASE / "sara/sara-3.jpg",
    "sofie":  BASE / "sofie/sofie-3.jpg",
    "atlas":  BASE / "atlas/atlas-3.jpg",
    "ales":   BASE / "ales/ales-3.jpg",
    "lumen":  BASE / "lumen/Lumen-3.jpg",    # velké L — soubor přejmenován na Lumen (ne Lumer)
    "muse":   BASE / "muse/muse-3.jpg",
    "samira": BASE / "samíra/Samira-3.jpg",  # velké S — soubor zatím nepřejmenován
    "vindex": BASE / "vindex/vindex-3.jpg",
}

JMENA = {
    "simona": "Simona", "sara": "Sára", "sofie": "Sofie",
    "atlas": "Atlas", "ales": "Aleš", "lumen": "Lumen",
    "muse": "Muse", "samira": "Samíra", "vindex": "Vindex",
}


def read_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"persona": None, "display": True}


def read_presence():
    """Vrátí seznam person s ON stavem z hospoda_presence.txt."""
    present = []
    try:
        with open(PRESENCE) as f:
            for line in f:
                line = line.strip()
                if "=ON" in line:
                    name = line.split("=")[0].strip().lower()
                    present.append(name)
    except Exception:
        pass
    return present


def load_image(path, size):
    """Načte obrázek a přizpůsobí velikosti (fill, zachová poměr)."""
    try:
        img = Image.open(path).convert("RGB")
        # Scale to fill (crop if needed)
        ratio = max(size[0] / img.width, size[1] / img.height)
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        # Crop center
        left = (new_w - size[0]) // 2
        top  = (new_h - size[1]) // 2
        img = img.crop((left, top, left + size[0], top + size[1]))
        return img
    except Exception:
        # Fallback: barevný placeholder
        img = Image.new("RGB", size, (50, 50, 70))
        return img


def make_speaking_frame(persona, sw, sh):
    """Fullscreen fotka mluvícího + jméno dole."""
    photo_path = PHOTOS.get(persona)
    img = load_image(photo_path, (sw, sh)) if photo_path else Image.new("RGB", (sw, sh), (30, 30, 50))

    # Tmavý pruh dole s jménem
    draw = ImageDraw.Draw(img)
    strip_h = max(80, sh // 10)
    draw.rectangle([(0, sh - strip_h), (sw, sh)], fill=(0, 0, 0, 180))
    jmeno = JMENA.get(persona, persona.capitalize())
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", strip_h // 2)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), jmeno, font=font)
    tw = bbox[2] - bbox[0]
    tx = (sw - tw) // 2
    ty = sh - strip_h + (strip_h - (bbox[3] - bbox[1])) // 2
    draw.text((tx, ty), jmeno, fill=(255, 255, 255), font=font)
    return img


def make_idle_frame(present, sw, sh):
    """table.jpg na pozadí + miniatury přítomných dole."""
    bg = load_image(TABLE_IMG, (sw, sh)) if TABLE_IMG.exists() else Image.new("RGB", (sw, sh), (35, 55, 35))

    if not present:
        return bg

    # Miniatury: řada dole, max 8, výška = sh//3
    n = min(len(present), 8)
    thumb_h = sh // 3
    thumb_w = min(sw // n, int(thumb_h * 0.75))
    total_w = thumb_w * n
    start_x = (sw - total_w) // 2
    y = sh - thumb_h - 10

    draw = ImageDraw.Draw(bg)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", thumb_h // 8)
    except Exception:
        font = ImageFont.load_default()

    for i, persona in enumerate(present[:8]):
        x = start_x + i * thumb_w
        photo_path = PHOTOS.get(persona)
        thumb = load_image(photo_path, (thumb_w - 4, thumb_h - 30)) if photo_path else Image.new("RGB", (thumb_w - 4, thumb_h - 30), (60, 60, 80))
        bg.paste(thumb, (x + 2, y))

        # Jméno pod fotkou
        jmeno = JMENA.get(persona, persona.capitalize())
        bbox = draw.textbbox((0, 0), jmeno, font=font)
        tw = bbox[2] - bbox[0]
        tx = x + (thumb_w - tw) // 2
        draw.rectangle([(x, y + thumb_h - 28), (x + thumb_w, y + thumb_h)], fill=(0, 0, 0))
        draw.text((tx, y + thumb_h - 26), jmeno, fill=(255, 255, 255), font=font)

    return bg


class SpeakerDisplay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)       # žádná titulní lišta
        self.root.attributes("-topmost", True)  # vždy navrchu
        self.root.attributes("-fullscreen", True)

        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()

        self.label = tk.Label(self.root, bg="black")
        self.label.pack(fill="both", expand=True)

        self._current_persona = "INIT"
        self._current_present = []
        self._visible = True
        self._tk_image = None  # drží referenci aby GC nesmazal

        self.root.after(100, self.poll)

    def set_image(self, pil_img):
        tk_img = ImageTk.PhotoImage(pil_img)
        self.label.config(image=tk_img)
        self._tk_image = tk_img  # zabrán reference

    def show(self):
        if not self._visible:
            self.root.deiconify()
            self._visible = True
            self._current_persona = "INIT"  # vynutí překreslení

    def hide(self):
        if self._visible:
            self.root.withdraw()
            self._visible = False

    def poll(self):
        state = read_state()
        display = state.get("display", True)
        persona = state.get("persona")

        if not display:
            self.hide()
        else:
            self.show()
            if self._visible:
                if persona:
                    if persona != self._current_persona:
                        img = make_speaking_frame(persona, self.sw, self.sh)
                        self.set_image(img)
                        self._current_persona = persona
                        self._current_present = []
                else:
                    present = read_presence()
                    if present != self._current_present or self._current_persona is not None:
                        img = make_idle_frame(present, self.sw, self.sh)
                        self.set_image(img)
                        self._current_persona = None
                        self._current_present = present

        self.root.after(POLL_MS, self.poll)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    # Počkej na STATE_FILE nebo vytvoř výchozí
    if not STATE_FILE.exists():
        with open(STATE_FILE, "w") as f:
            json.dump({"persona": None, "display": True}, f)
    SpeakerDisplay().run()
