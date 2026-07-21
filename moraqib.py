#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import json
import os

# ============ CONFIGURATION ============
URL = "https://trouverunlogement.lescrous.fr/tools/47/search?bounds=2.9679677_50.6612596_3.125725_50.6008264&locationName=Lille"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

STATE_FILE = "state.txt"
# ========================================


def get_listing_count():
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(URL, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    for script_tag in soup.find_all("script", attrs={"data-sveltekit-fetched": True}):
        data_url = script_tag.get("data-url", "")
        if "/api/fr/search/" in data_url:
            outer_json = json.loads(script_tag.string)
            inner_body = json.loads(outer_json["body"])
            return inner_body["results"]["total"]["value"]

    print("⚠️ Impossible de trouver le compteur JSON, structure de page peut-être changée.")
    return 0


def read_previous_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return f.read().strip() == "available"
    return False


def write_state(available):
    with open(STATE_FILE, "w") as f:
        f.write("available" if available else "unavailable")


def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram non configuré.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    print(f"Telegram status code: {response.status_code}")
    print(f"Telegram response: {response.text}")


def main():
    was_available = read_previous_state()
    count = get_listing_count()
    available = count > 0

    print(f"Nombre de logs trouvés : {count}")
    print(f"Disponible : {available} (précédemment : {was_available})")

    if available and not was_available:
        message = (
            f"Un log est disponible pour (2026-2027) !\n"
            f"{count} log trouvé(s).\n"
            f"Va vite vérifier : {URL}"
        )
        print("🚨 Nouveau log détecté, envoi de l'alerte...")
        send_telegram_alert(message)

    write_state(available)


if __name__ == "__main__":
    main()
