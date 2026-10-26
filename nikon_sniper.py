import json
import os
import re
import urllib.request
from playwright.sync_api import sync_playwright

# ================= CONFIGURATION =================
# Store your Bark key in GitHub Secrets as BARK_KEY (or paste it here)
BARK_KEY = os.environ.get("BARK_KEY", "HjN2veHS4hHmpP6Mhc2kcP")
REFURB_MAIN_URL = "https://www.nikonusa.com/refurbished-cameras"
STATE_FILE = "state.json"

WATCHLIST = [
    {
        "name": "NIKKOR Z 70-200mm f/2.8 VR S (Refurb)",
        "url": "https://www.nikonusa.com/p/nikkor-z-70-200mm-f28-vr-s-refurbished/20092B",
        "max_price": 1950.00,
    },
    {
        "name": "NIKKOR Z MC 105mm f/2.8 VR S (Refurb)",
        "url": "https://www.nikonusa.com/p/nikkor-z-mc-105mm-f28-vr-s-refurbished/20100B",
        "max_price": 780.00,
    },
]

SALE_KEYWORDS = [
    "nikon",  # <-- Temporary test trigger!
    "extra 10%",
    "additional 10%",
    "save an extra",
    "10% off refurbished",
    "discount applied in cart",
]
# =================================================


def send_push_alert(title: str, message: str, target_url: str):
    """Sends an instant push notification to iPhone via Bark API."""
    if not BARK_KEY:
        print("BARK_KEY not set. Skipping push alert.")
        return

    payload = {
        "device_key": BARK_KEY,
        "title": title,
        "body": message,
        "url": target_url,  # Tapping the notification opens this URL in Safari
        "group": "nikon",
        "sound": "calypso",  # Distinctive alert sound
        "icon": "https://www.nikonusa.com/favicon.ico",
    }

    req = urllib.request.Request(
        "https://api.day.app/push",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print(f"Sent Bark alert: {title}")
    except Exception as e:
        print(f"Failed to send Bark alert: {e}")
