import os
import json
import logging
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TravelGuard",
    description="Travel safety assistant for first-time travelers",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load data files
def load_json_data(filepath: str) -> dict:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Data file not found: {filepath}")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in: {filepath}")
        return {}

emigration_rules = load_json_data("data/emigration_rules.json")
restricted_items = load_json_data("data/restricted_items.json")


@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/api/offer-check")
async def offer_check(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    language: str = Form("en")
):
    if not text and not image:
        raise HTTPException(status_code=400, detail="Please provide either text or an image of the offer.")
    
    try:
        from services.offer_check import analyze_offer
        image_bytes = None
        if image:
            image_bytes = await image.read()
        result = await analyze_offer(text, image_bytes, language, emigration_rules)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Offer check error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "We couldn't analyze the offer right now. Please try again.",
                "fallback": {
                    "risk_score": -1,
                    "risk_level": "unknown",
                    "red_flags": ["Service temporarily unavailable"],
                    "what_to_verify": ["Try again in a few moments"],
                    "safe_next_steps": ["Contact official emigration helpline: 1800-11-3090"]
                }
            }
        )


@app.post("/api/pack-check")
async def pack_check(
    items: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    destination: str = Form("UAE"),
    language: str = Form("en")
):
    if not items and not image:
        raise HTTPException(status_code=400, detail="Please provide a list of items or upload an image.")
    
    try:
        from services.pack_check import analyze_items
        image_bytes = None
        if image:
            image_bytes = await image.read()
        result = await analyze_items(items, image_bytes, destination, language, restricted_items)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Pack check error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "We couldn't check your items right now. Please try again."
            }
        )


@app.post("/api/checklist")
async def checklist(
    destination: str = Form("UAE"),
    purpose: str = Form("work"),
    travel_date: str = Form(...),
    layover_hours: Optional[float] = Form(None),
    language: str = Form("en")
):
    try:
        from services.checklist import generate_checklist
        result = await generate_checklist(destination, purpose, travel_date, layover_hours, language, emigration_rules)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Checklist error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "We couldn't generate your checklist right now. Please try again."
            }
        )


@app.get("/api/handbag")
async def get_handbag_checklist():
    """Load curated handbag must-have, battery rules, and cabin luggage suggestions."""
    try:
        with open("data/handbag_items.json", "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    except Exception as e:
        logger.error(f"Error loading handbag items: {e}")
        raise HTTPException(status_code=500, detail="Could not load handbag checklist data.")


@app.get("/api/currency")
async def currency_converter(
    from_curr: str = "AED",
    to_curr: str = "INR",
    amount: float = 1.0,
    language: str = "en"
):
    """Real-time exchange rate with cached fallback and airport vs city exchange tips."""
    try:
        from services.currency_service import get_exchange_rate
        result = await get_exchange_rate(from_curr, to_curr, amount, language)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Currency error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "Failed to calculate currency exchange rate."}
        )


@app.post("/api/boarding-guide")
async def boarding_guide(
    departure_airport: str = Form("COK"),
    flight_time: str = Form("14:30"),
    is_international: bool = Form(True),
    has_checked_bag: bool = Form(True),
    has_ecr_passport: bool = Form(False),
    language: str = Form("en")
):
    """Generate airport arrival & gate countdown timeline with live 'what to do now' status."""
    try:
        from services.boarding_guide import generate_boarding_timeline
        result = generate_boarding_timeline(
            departure_airport=departure_airport,
            flight_time_str=flight_time,
            is_international=is_international,
            has_checked_bag=has_checked_bag,
            has_ecr_passport=has_ecr_passport,
            language=language
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Boarding guide error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "Failed to generate boarding timeline."}
        )


@app.post("/api/sim-guide")
async def sim_guide(
    arrival_city: str = Form("Dubai"),
    stay_days: int = Form(7),
    data_usage: str = Form("medium"),
    user_type: str = Form("visitor"),
    language: str = Form("en")
):
    """Recommend verified UAE SIM plans (e&, du, Virgin) directly from curated data."""
    try:
        from services.sim_service import get_sim_recommendations
        result = get_sim_recommendations(
            arrival_city=arrival_city,
            stay_days=stay_days,
            data_usage=data_usage,
            user_type=user_type,
            language=language
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"SIM guide error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "Failed to load SIM plans."}
        )


@app.post("/api/contract-check")
async def contract_check(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    language: str = Form("en")
):
    """Analyze employment contracts for passport retention, salary, overtime, and red flags."""
    if not text and not image:
        raise HTTPException(status_code=400, detail="Please upload a contract image or paste contract text.")

    try:
        from services.contract_reader import analyze_contract
        image_bytes = None
        if image:
            image_bytes = await image.read()
        result = await analyze_contract(text, image_bytes, language)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Contract check error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "Could not analyze the employment contract."}
        )


@app.get("/api/emergency-card")
async def emergency_card(language: str = "en"):
    """Emergency numbers, embassy contacts, and NORKA-Roots helplines with tap-to-call."""
    is_ml = language == "ml"
    is_hi = language == "hi"

    contacts = [
        {
            "name": "NORKA-Roots 24/7 Expatriate Helpline" if not is_ml else "നോർക്ക-റൂട്ട്സ് 24/7 പ്രവാസി ഹെൽപ്പ്‌ലൈൻ",
            "number": "1800-425-3939",
            "alt_number": "+91-471-2333339",
            "desc": "Government of Kerala support for Gulf returnees & issues" if not is_ml else "കേരള സർക്കാർ പ്രവാസി സഹായ കേന്ദ്രം",
            "category": "expat_support",
            "icon": "🌴"
        },
        {
            "name": "Indian Embassy Abu Dhabi" if not is_ml else "ഇന്ത്യൻ എംബസി അബുദാബി",
            "number": "+971-2-4492700",
            "alt_number": "+971-50-8995588",
            "desc": "24/7 Emergency consular assistance" if not is_ml else "24 മണിക്കൂർ അടിയന്തര കോൺസുലാർ സഹായം",
            "category": "embassy",
            "icon": "🏛️"
        },
        {
            "name": "Consulate General of India (Dubai)" if not is_ml else "ഇന്ത്യൻ കോൺസുലേറ്റ് ദുബായ്",
            "number": "+971-4-3971222",
            "alt_number": "800-46342",
            "desc": "Toll-free emergency help for Dubai, Sharjah, Ajman, RAK, Fujairah" if not is_ml else "ദുബായിലും വടക്കൻ എമിറേറ്റുകളിലുമുള്ള സഹായം",
            "category": "embassy",
            "icon": "🇮🇳"
        },
        {
            "name": "eMigrate PBSK Overseas Helpline" if not is_ml else "eMigrate വിദേശകാര്യ മന്ത്രാലയ ഹെൽപ്പ്‌ഡെസ്ക്",
            "number": "1800-11-3090",
            "alt_number": "+91-11-26887770",
            "desc": "Ministry of External Affairs illegal recruitment report line" if not is_ml else "വ്യാജ റിക്രൂട്ട്മെന്റ് റിപ്പോർട്ടിംഗ് ലൈൻ",
            "category": "emigration",
            "icon": "⚖️"
        },
        {
            "name": "UAE Police Emergency" if not is_ml else "യുഎഇ പോലീസ് അടിയന്തരം",
            "number": "999",
            "alt_number": "",
            "desc": "Toll-free emergency police dispatch across all Emirates" if not is_ml else "എല്ലാ എമിറേറ്റുകളിലും സൗജന്യ അടിയന്തര നമ്പർ",
            "category": "local_emergency",
            "icon": "🚨"
        },
        {
            "name": "UAE Ambulance / Medical" if not is_ml else "യുഎഇ ആംബുലൻസ്",
            "number": "998",
            "alt_number": "",
            "desc": "Emergency medical and paramedic service" if not is_ml else "അടിയന്തര വൈദ്യസഹായം",
            "category": "local_emergency",
            "icon": "🚑"
        },
        {
            "name": "UAE MOHRE Labor Helpline" if not is_ml else "യുഎഇ തൊഴിൽ മന്ത്രാലയ ഹെൽപ്പ്‌ലൈൻ",
            "number": "800-60",
            "alt_number": "04-665-9999",
            "desc": "Report labor disputes, unpaid wages, or withheld passports" if not is_ml else "ശമ്പള കുടിശ്ശിക, പാസ്‌പോർട്ട് പിടിച്ചുവെക്കൽ പരാതികൾ",
            "category": "labor_rights",
            "icon": "💼"
        }
    ]

    return JSONResponse(content={
        "language": language,
        "contacts": contacts,
        "verified_source": "Ministry of External Affairs India, NORKA-Roots, and UAE Government Emergency Services"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run("main:app", host=host, port=port, reload=True)


