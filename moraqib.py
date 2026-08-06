#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import json
import os

# ============ CONFIGURATION ============
LOCATIONS = {
    "Lille": "https://trouverunlogement.lescrous.fr/tools/47/search?bounds=2.9679677_50.6612596_3.125725_50.6008264&locationName=Lille",
    "Villeneuve-d'Ascq": "https://trouverunlogement.lescrous.fr/tools/47/search?bounds=3.1158064_50.6732934_3.2078132_50.5985301&locationName=Villeneuve-d%27Ascq",
    "Mons-en-Barœul": "https://trouverunlogement.lescrous.fr/tools/47/search?bounds=3.0933912_50.6529864_3.1249645_50.634256&locationName=Mons-en-Bar%C5%93ul+%2859370%29",
    "Roubaix": "https://trouverunlogement.lescrous.fr/tools/47/search?bounds=3.1511381_50.7087385_3.2174443_50.6687414&locationName=Roubaix",
    "Wattignies": "https://trouverunlogement.lescrous.fr/tools/47/search?bounds=3.012419_50.6012678_3.0655836_50.5710624&locationName=Wattignies+%2859139%29",
}

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

STATE_FILE = "state.json"
# ========================================


def get_listing_count(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    for script_tag in soup.find_all("script", attrs={"data-sveltekit-fetched": True}):
        data_url = script_tag.get("data-url", "")
        if "/api/fr/search/" in data_url:
            outer_json = json.loads(script_tag.string)
            inner_body = json.loads(outer_json["body"])
            return inner_body["results"]["total"]["value"]

    print(f"⚠️ Impossible de trouver le compteur JSON pour {url}, structure de page peut-être changée.")
    return 0


def read_previous_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def write_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram non configuré.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    print(f"Telegram status code: {response.status_code}")
    print(f"Telegram response: {response.text}")


def main():
    previous_state = read_previous_state()
    new_state = {}

    for name, url in LOCATIONS.items():
        was_available = previous_state.get(name, False)

        try:
            count = get_listing_count(url)
        except Exception as e:
            print(f"❌ Erreur pour {name} : {e}")
            # keep previous known state on error, so a transient failure
            # doesn't wrongly reset the "already alerted" status
            new_state[name] = was_available
            continue

        available = count > 0
        print(f"[{name}] Nombre de logs trouvés : {count} | Disponible : {available} (précédemment : {was_available})")

        if available and not was_available:
            message = (
                f"Un logement est disponible à {name} (2026-2027) !\n"
                f"{count} logement(s) trouvé(s).\n"
                f"Va vite vérifier : {url}"
            )
            print(f"🚨 Nouveau logement détecté à {name}, envoi de l'alerte...")
            send_telegram_alert(message)

        new_state[name] = available

    write_state(new_state)


if __name__ == "__main__":
    main()
