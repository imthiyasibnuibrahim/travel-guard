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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
