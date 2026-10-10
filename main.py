import os
import json
import logging
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TravelGuard",
    description="Professional Travel Safety Assistant for Emigrants and Travelers",
    version="2.0.0"
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


# Pydantic Schemas for JSON Requests
class OfferCheckRequest(BaseModel):
    text_content: Optional[str] = None
    text: Optional[str] = None
    language: str = Field(default="en", description="en, ml, or hi")

class PackCheckRequest(BaseModel):
    items: Optional[str] = None
    destination: str = "UAE"
    language: str = "en"

class ChecklistRequest(BaseModel):
    destination: str = "UAE"
    purpose: str = "work"
    travel_date: str
    layover_hours: Optional[float] = None
    language: str = "en"


@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}


@app.post("/api/offer-check")
async def offer_check(
    request: Request,
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    language: str = Form("en")
):
    """
    Accepts both application/json (for programmatic API/test clients) 
    and multipart/form-data (for mobile camera photo uploads).
    """
    content_type = request.headers.get("content-type", "")
    image_bytes = None
    
    if "application/json" in content_type:
        try:
            body = await request.json()
            text = body.get("text_content") or body.get("text")
            language = body.get("language", "en")
        except Exception:
            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "error_type": "PARSING_ERROR",
                    "message": "Malformed JSON payload.",
                    "fallback_applied": False
                }
            )

    if image:
        try:
            image_bytes = await image.read()
        except Exception as e:
            logger.error(f"Failed to read image bytes: {e}")

    if not text and not image_bytes:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error_type": "VALIDATION_ERROR",
                "message": "Please provide either text or an image of the offer.",
                "fallback_applied": False
            }
        )
    
    try:
        from services.offer_check import analyze_offer
        result = await analyze_offer(text, image_bytes, language, emigration_rules)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Offer check error: {e}")
        from services.offer_check import rule_based_offer_fallback
        fallback_data = rule_based_offer_fallback(text, language)
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "fallback_applied": True,
                "message": "AI service temporarily busy; local verified emigration rules applied.",
                **fallback_data
            }
        )


@app.post("/api/pack-check")
async def pack_check(
    request: Request,
    items: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    destination: str = Form("UAE"),
    language: str = Form("en")
):
    """
    Accepts both application/json and multipart/form-data.
    """
    content_type = request.headers.get("content-type", "")
    image_bytes = None
    
    if "application/json" in content_type:
        try:
            body = await request.json()
            items = body.get("items")
            destination = body.get("destination", "UAE")
            language = body.get("language", "en")
        except Exception:
            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "error_type": "PARSING_ERROR",
                    "message": "Malformed JSON payload.",
                    "fallback_applied": False
                }
            )

    if image:
        try:
            image_bytes = await image.read()
        except Exception as e:
            logger.error(f"Failed to read pack image bytes: {e}")

    if not items and not image_bytes:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error_type": "VALIDATION_ERROR",
                "message": "Please provide a list of items or upload an image.",
                "fallback_applied": False
            }
        )
    
    try:
        from services.pack_check import analyze_items
        result = await analyze_items(items, image_bytes, destination, language, restricted_items)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Pack check error: {e}")
        from services.pack_check import rule_based_pack_fallback
        fallback_data = rule_based_pack_fallback(items, destination, language, restricted_items)
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "fallback_applied": True,
                **fallback_data
            }
        )


@app.post("/api/checklist")
async def checklist(
    request: Request,
    destination: str = Form("UAE"),
    purpose: str = Form("work"),
    travel_date: Optional[str] = Form(None),
    layover_hours: Optional[float] = Form(None),
    language: str = Form("en")
):
    """
    Accepts both application/json and multipart/form-data.
    """
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            destination = body.get("destination", "UAE")
            purpose = body.get("purpose", "work")
            travel_date = body.get("travel_date")
            layover_hours = body.get("layover_hours")
            language = body.get("language", "en")
        except Exception:
            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "error_type": "PARSING_ERROR",
                    "message": "Malformed JSON payload.",
                    "fallback_applied": False
                }
            )

    if not travel_date:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error_type": "VALIDATION_ERROR",
                "message": "Please specify a travel_date.",
                "fallback_applied": False
            }
        )

    try:
        from services.checklist import generate_checklist
        result = await generate_checklist(destination, purpose, travel_date, layover_hours, language, emigration_rules)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Checklist error: {e}")
        from services.checklist import rule_based_checklist_fallback
        fallback_data = rule_based_checklist_fallback(destination, purpose, travel_date, layover_hours, language, emigration_rules)
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "fallback_applied": True,
                **fallback_data
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
    """Recommend verified UAE SIM plans (e&, du, Virgin, eSIMs) with confidence badges."""
    try:
        from services.sim_service import get_sim_recommendations
        result = await get_sim_recommendations(
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
            "name": "NORKA-Roots 24/7 Expatriate Helpline" if not is_ml and not is_hi else ("നോർക്ക-റൂട്ട്സ് 24/7 പ്രവാസി ഹെൽപ്പ്‌ലൈൻ" if is_ml else "नोर्का-रूट्स 24/7 प्रवासी हेल्पलाइन"),
            "number": "1800-425-3939",
            "alt_number": "+91-471-2333339",
            "desc": "Government of Kerala support for Gulf returnees & issues" if not is_ml and not is_hi else ("കേരള സർക്കാർ പ്രവാസി സഹായ കേന്ദ്രം" if is_ml else "केरल सरकार प्रवासी सहायता केंद्र"),
            "category": "expat_support",
            "icon": "🌴"
        },
        {
            "name": "Indian Embassy Abu Dhabi" if not is_ml and not is_hi else ("ഇന്ത്യൻ എംബസി അബുദാബി" if is_ml else "भारतीय दूतावास अबू धाबी"),
            "number": "+971-2-4492700",
            "alt_number": "+971-50-8995588",
            "desc": "24/7 Emergency consular assistance" if not is_ml and not is_hi else ("24 മണിക്കൂർ അടിയന്തര കോൺസുലാർ സഹായം" if is_ml else "24 घंटे आपातकालीन कांसुलर सहायता"),
            "category": "embassy",
            "icon": "🏛️"
        },
        {
            "name": "Consulate General of India (Dubai)" if not is_ml and not is_hi else ("ഇന്ത്യൻ കോൺസുലേറ്റ് ദുബായ്" if is_ml else "भारतीय वाणिज्य दूतावास दुबई"),
            "number": "+971-4-3971222",
            "alt_number": "800-46342",
            "desc": "Toll-free emergency help for Dubai, Sharjah, Ajman, RAK, Fujairah" if not is_ml and not is_hi else ("ദുബായിലും വടക്കൻ എമിറേറ്റുകളിലുമുള്ള സഹായം" if is_ml else "दुबई और उत्तरी अमीरात के लिए सहायता"),
            "category": "embassy",
            "icon": "🇮🇳"
        },
        {
            "name": "eMigrate PBSK Overseas Helpline" if not is_ml and not is_hi else ("eMigrate വിദേശകാര്യ മന്ത്രാലയ ഹെൽപ്പ്‌ഡെസ്ക്" if is_ml else "ई-माइग्रेट प्रवासी हेल्पलाइन"),
            "number": "1800-11-3090",
            "alt_number": "+91-11-26887770",
            "desc": "Ministry of External Affairs illegal recruitment report line" if not is_ml and not is_hi else ("വ്യാജ റിക്രൂട്ട്മെന്റ് റിപ്പോർട്ടിംഗ് ലൈൻ" if is_ml else "अवैध भर्ती शिकायत नंबर"),
            "category": "emigration",
            "icon": "⚖️"
        },
        {
            "name": "UAE Police Emergency" if not is_ml and not is_hi else ("യുഎഇ പോലീസ് അടിയന്തരം" if is_ml else "यूएई पुलिस आपातकालीन"),
            "number": "999",
            "alt_number": "",
            "desc": "Toll-free emergency police dispatch across all Emirates" if not is_ml and not is_hi else ("എല്ലാ എമിറേറ്റുകളിലും സൗജന്യ അടിയന്തര നമ്പർ" if is_ml else "सभी अमीरात में टोल-फ्री पुलिस सहायता"),
            "category": "local_emergency",
            "icon": "🚨"
        },
        {
            "name": "UAE Ambulance / Medical" if not is_ml and not is_hi else ("യുഎഇ ആംബുലൻസ്" if is_ml else "यूएई एम्बुलेंस"),
            "number": "998",
            "alt_number": "",
            "desc": "Emergency medical and paramedic service" if not is_ml and not is_hi else ("അടിയന്തര വൈദ്യസഹായം" if is_ml else "आपातकालीन चिकित्सा सेवा"),
            "category": "local_emergency",
            "icon": "🚑"
        },
        {
            "name": "UAE MOHRE Labor Helpline" if not is_ml and not is_hi else ("യുഎഇ തൊഴിൽ മന്ത്രാലയ ഹെൽപ്പ്‌ലൈൻ" if is_ml else "यूएई श्रम मंत्रालय हेल्पलाइन"),
            "number": "800-60",
            "alt_number": "04-665-9999",
            "desc": "Report labor disputes, unpaid wages, or withheld passports" if not is_ml and not is_hi else ("ശമ്പള കുടിശ്ശിക, പാസ്‌പോർട്ട് പിടിച്ചുവെക്കൽ പരാതികൾ" if is_ml else "वेतन और पासपोर्ट जब्ती शिकायत नंबर"),
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
