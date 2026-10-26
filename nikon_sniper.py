import json
import os
import re
import urllib.request
from playwright.sync_api import sync_playwright

# ================= CONFIGURATION =================
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
REFURB_MAIN_URL = "https://www.nikonusa.com/refurbished-cameras"
STATE_FILE = "state.json"

# Specific lenses/bodies to snipe:
# Set "max_price" slightly below normal refurb price so it triggers on the extra 10% drop
WATCHLIST = [
    {
        "name": "NIKKOR Z 70-200mm f/2.8 VR S (Refurb)",
        "url": "https://www.nikonusa.com/p/nikkor-z-70-200mm-f28-vr-s-refurbished/20092B",
        "max_price": 1950.00,  # Normal refurb is ~$2,159; 10% off drops it to ~$1,943
    },
    {
        "name": "NIKKOR Z MC 105mm f/2.8 VR S (Refurb)",
        "url": "https://www.nikonusa.com/p/nikkor-z-mc-105mm-f28-vr-s-refurbished/20100B",
        "max_price": 780.00,   # Normal refurb is ~$849; 10% off drops it to ~$764
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
    """Sends a high-priority push notification to iPhone/Apple Watch via ntfy.sh."""
    if not NTFY_TOPIC:
        print("NTFY_TOPIC secret not set. Skipping push alert.")
        return

    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": "5",  # Max priority (bypasses normal quiet notifications)
            "Tags": "rotating_light,camera",
            "Click": target_url,  # Tapping the alert opens the Nikon page directly
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print(f"Sent alert: {title}")
    except Exception as e:
        print(f"Failed to send ntfy alert: {e}")


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"banner_active": False, "items": {}}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def extract_lowest_price(text: str):
    """Extracts dollar prices like $1,943.95 from product text."""
    matches = re.findall(r"\$([0-9]{1,2},?[0-9]{3}\.[0-9]{2}|[0-9]{3}\.[0-9]{2})", text)
    prices = [float(m.replace(",", "")) for m in matches]
    return min(prices) if prices else None


def check_nikon():
    state = load_state()

    with sync_playwright() as p:
        # Use stealth flags so Akamai does not block GitHub Actions runner IPs
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )
        page = context.new_page()

        # 1. Check Main Refurbished Landing Page for Promo Banner
        try:
            page.goto(REFURB_MAIN_URL, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            body_text = page.inner_text("body").lower()

            matched_keyword = next((kw for kw in SALE_KEYWORDS if kw in body_text), None)
            if matched_keyword and not state.get("banner_active"):
                send_push_alert(
                    title="NIKON 10% REFURB SALE LIVE!",
                    message=f"Detected '{matched_keyword}' on Nikon USA Refurbished page. Tap to open!",
                    target_url=REFURB_MAIN_URL,
                )
                state["banner_active"] = True
            elif not matched_keyword:
                state["banner_active"] = False
        except Exception as e:
            print(f"Error checking main page: {e}")

        # 2. Check Specific Watchlist Items for Stock + Price Drop
        for item in WATCHLIST:
            try:
                page.goto(item["url"], timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)
                page_text = page.inner_text("body")
                page_lower = page_text.lower()

                in_stock = "add to cart" in page_lower and "out of stock" not in page_lower[:1500]
                current_price = extract_lowest_price(page_text)

                item_key = item["name"]
                prev_alerted = state["items"].get(item_key, False)

                if in_stock and current_price and current_price <= item["max_price"]:
                    if not prev_alerted:
                        send_push_alert(
                            title=f"IN STOCK: ${current_price:.2f}",
                            message=f"{item['name']} is in stock at ${current_price:.2f} (Target <= ${item['max_price']})!",
                            target_url=item["url"],
                        )
                        state["items"][item_key] = True
                else:
                    state["items"][item_key] = False

            except Exception as e:
                print(f"Error checking {item['name']}: {e}")

        browser.close()

    save_state(state)


if __name__ == "__main__":
    check_nikon()
