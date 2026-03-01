#!/usr/bin/env python3
"""
hospoda_pinger.py — sleduje hospoda.txt a pinguje AI dívky když přibydou nové zprávy.
Použití: python3 hospoda_pinger.py
Zastavení: Ctrl+C
"""

import time
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright

HOSPODA_FILE = "/home/ales/AI-CIVILIZATION/hospoda.txt"
CHECK_INTERVAL = 30    # kontrola souboru každých 30 sekund
MIN_PING_GAP   = 120   # min. sekund mezi pingy stejné dívky (ochrana proti spamu)

GIRLS = {
    "simona": "https://claude.ai/chat/c5f964e5-c9b3-4bcd-9509-3ce406751d2e",
    "sara":   "https://claude.ai/chat/8824991d-a4ad-4e6d-a0b5-a96a3bbd74d7",
    "sofie":  "https://claude.ai/chat/a22aa932-3bf9-4f8a-b4ed-9bcd47491b93",
}

CHROME_PROFILE = "/home/ales/.config/google-chrome-pinger"


def count_msgs():
    try:
        result = subprocess.run(
            ["grep", "-c", ">>", HOSPODA_FILE],
            capture_output=True, text=True
        )
        return int(result.stdout.strip())
    except Exception:
        return 0


def ping_girl(page, name, url):
    try:
        log(f"Pinguji {name}...")
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        # Claude.AI používá ProseMirror editor
        field = page.wait_for_selector(".ProseMirror", timeout=10000)
        field.click()
        page.keyboard.type(".")
        page.keyboard.press("Enter")
        log(f"{name} pingnuta ✓")
        time.sleep(3)  # počkej než se zpráva odešle
        return True
    except Exception as e:
        log(f"CHYBA {name}: {e}")
        return False


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    last_count = count_msgs()
    last_ping = {name: 0 for name in GIRLS}

    log(f"Hospoda pinger spuštěn. Zpráv: {last_count}. Interval: {CHECK_INTERVAL}s")
    log("Zastav pomocí Ctrl+C")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_PROFILE,
            headless=False,
            channel="chrome",
            args=["--no-first-run", "--no-default-browser-check"]
        )
        page = browser.new_page()

        try:
            while True:
                time.sleep(CHECK_INTERVAL)
                current_count = count_msgs()

                if current_count > last_count:
                    now = time.time()
                    log(f"{current_count - last_count} nových zpráv ({last_count}→{current_count})")
                    last_count = current_count

                    for name, url in GIRLS.items():
                        elapsed = now - last_ping[name]
                        if elapsed >= MIN_PING_GAP:
                            if ping_girl(page, name, url):
                                last_ping[name] = now
                        else:
                            log(f"  {name}: příliš brzy, čekám ještě {int(MIN_PING_GAP - elapsed)}s")
                else:
                    log(f"Nic nového ({current_count} zpráv), čekám...")

        except KeyboardInterrupt:
            log("Pinger zastaven.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
