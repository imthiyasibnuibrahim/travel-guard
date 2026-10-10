import os
import json
import logging
from datetime import datetime, timezone
import httpx

logger = logging.getLogger(__name__)

CACHE_FILE = "data/currency_cache.json"

DEFAULT_RATES = {
    "base_code": "AED",
    "rates": {
        "INR": 26.38,
        "AED": 1.0,
        "USD": 0.272,
        "SAR": 1.02,
        "QAR": 0.99,
        "OMR": 0.105,
        "KWD": 0.083,
        "BHD": 0.103,
        "EUR": 0.25
    },
    "time_last_update_utc": "2026-10-10 12:00:00 UTC"
}


def load_cached_rates() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading currency cache: {e}")
    return DEFAULT_RATES


def save_cached_rates(data: dict):
    try:
        os.makedirs("data", exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving currency cache: {e}")


async def get_exchange_rate(
    from_curr: str = "AED",
    to_curr: str = "INR",
    amount: float = 1.0,
    language: str = "en"
) -> dict:
    from_curr = from_curr.upper()
    to_curr = to_curr.upper()
    
    rates_data = None
    source = "live_api"

    # Try live fetch
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(f"https://open.er-api.com/v6/latest/{from_curr}")
            if resp.status_code == 200:
                json_resp = resp.json()
                if "rates" in json_resp:
                    rates_data = json_resp
                    save_cached_rates(rates_data)
    except Exception as e:
        logger.warning(f"Live currency API failed, using cache: {e}")

    # Fallback to cache
    if not rates_data:
        rates_data = load_cached_rates()
        source = "cached_fallback"

    rates = rates_data.get("rates", {})
    rate = rates.get(to_curr)

    # Cross rate calculation if base is different
    if rate is None:
        if from_curr in rates and to_curr in rates:
            rate = rates[to_curr] / rates[from_curr]
        elif from_curr == to_curr:
            rate = 1.0
        else:
            rate = 26.38 if (from_curr == "AED" and to_curr == "INR") else 1.0

    converted = round(amount * rate, 2)
    last_updated = rates_data.get("time_last_update_utc", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    tips = {
        "en": "Exchange Tip: Airport currency counters charge 5% to 8% markup. Exchange only minimal taxi fare at the airport, and use city exchanges (like Al Ansari, LuLu Exchange) for better rates.",
        "ml": "കറൻസി ടിപ്പ്: എയർപോർട്ട് എക്സ്ചേഞ്ചുകളിൽ 5% മുതൽ 8% വരെ കൂടുതൽ ചാർജ് ഈടാക്കാറുണ്ട്. അടിയന്തര ആവശ്യത്തിനുള്ള തുക മാത്രം എയർപോർട്ടിൽ മാറ്റി ബാക്കി സിറ്റിയിലെ ലുലു അല്ലെങ്കിൽ അൽ അൻസാരി എക്സ്ചേഞ്ച് വഴി മാറ്റുക.",
        "hi": "मुद्रा विनिमय सुझाव: हवाई अड्डे के काउंटरों पर 5% से 8% अतिरिक्त शुल्क लगता है। हवाई अड्डे पर केवल थोड़ा टैक्सी किराया बदलें और शेष राशि शहर के अधिकृत केंद्रों से बदलें।"
    }

    return {
        "from_currency": from_curr,
        "to_currency": to_curr,
        "amount": amount,
        "exchange_rate": round(rate, 4),
        "converted_amount": converted,
        "last_updated": last_updated,
        "source": source,
        "tip": tips.get(language, tips["en"])
    }
