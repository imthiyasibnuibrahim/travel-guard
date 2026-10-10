import json
import logging
from typing import Optional
from services.gemini_service import ask_gemini
from services.currency_service import get_exchange_rate

logger = logging.getLogger(__name__)

# Load dataset once at startup
SIM_DATASET = {}
try:
    with open("data/sim_plans.json", "r", encoding="utf-8") as f:
        SIM_DATASET = json.load(f)
    logger.info(f"Loaded sim_plans.json with {len(SIM_DATASET.get('plans', []))} plans.")
except Exception as e:
    logger.error(f"Failed to load sim_plans.json at startup: {e}")
    SIM_DATASET = {"meta": {}, "plans": []}


def get_sim_dataset() -> dict:
    global SIM_DATASET
    if not SIM_DATASET or not SIM_DATASET.get("plans"):
        try:
            with open("data/sim_plans.json", "r", encoding="utf-8") as f:
                SIM_DATASET = json.load(f)
        except Exception:
            pass
    return SIM_DATASET


async def get_sim_recommendations(
    arrival_city: str = "Dubai",
    stay_days: int = 7,
    data_usage: str = "medium",  # light, medium, heavy, or specific
    user_type: str = "visitor",  # visitor/tourist or resident/job_seeker
    language: str = "en"
) -> dict:
    dataset = get_sim_dataset()
    meta = dataset.get("meta", {})
    all_plans = dataset.get("plans", [])

    # 1. Inputs conversion to numeric & validation
    try:
        days = int(stay_days)
    except (ValueError, TypeError):
        days = 7
    if days <= 0:
        days = 7

    usage_map = meta.get("usage_guide_gb_per_day", {
        "light_maps_messaging": 0.3,
        "medium_social_video_calls": 1.0,
        "heavy_streaming_hotspot_work": 3.0
    })

    usage_key = "medium_social_video_calls"
    if "light" in data_usage.lower():
        usage_key = "light_maps_messaging"
    elif "heavy" in data_usage.lower():
        usage_key = "heavy_streaming_hotspot_work"

    gb_per_day = usage_map.get(usage_key, 1.0)
    estimated_gb_needed = round(days * gb_per_day, 1)

    # Fetch live/cached exchange rate for AED -> INR
    curr_res = await get_exchange_rate("AED", "INR", 1.0, language)
    aed_to_inr = curr_res.get("exchange_rate", 26.38)

    # 2. Filter plans in code (not in LLM)
    is_resident = (user_type.lower() == "resident")

    filtered_candidates = []
    for plan in all_plans:
        # Exclude resident-only plans if tourist
        suitable = plan.get("suitable_for", [])
        if not is_resident and "resident" in suitable:
            continue

        # Check validity: covers the trip (or if trip > 28 days, keep plans >= 28 days with repurchase note)
        val_days = plan.get("validity_days") or 1
        if days <= 28:
            # Plan must be at least the trip days or close
            # But allow 7-day plans for 7 days, 10-day for 10 days, etc.
            # If trip is 10 days, a 7-day plan alone won't cover unless unlimited or user buys again.
            # Allow plans where val_days >= days, OR unlimited plans for 7/10 days
            if val_days < days and not (plan.get("unlimited_data") and days <= 14):
                # Don't strictly discard 28-day plans for a 7-day trip (28 days easily covers 7 days)
                continue
        else:
            # Stays over 28 days: keep 28+ day plans
            if val_days < 28:
                continue

        # Check data sufficiency:
        # Keep if unlimited_data is True, OR data_gb >= estimated_gb_needed, OR product is cheap eSIM option
        data_gb = plan.get("data_gb")
        is_unlimited = bool(plan.get("unlimited_data"))
        has_enough_data = is_unlimited or (data_gb is not None and data_gb >= estimated_gb_needed)

        # Calculate price in AED
        price_aed = plan.get("price_aed")
        if price_aed is None and plan.get("price_usd_approx"):
            # Convert USD to AED (~3.6725)
            price_aed = round(plan["price_usd_approx"] * 3.6725, 2)
            plan["price_aed_calc"] = price_aed
        else:
            plan["price_aed_calc"] = price_aed if price_aed is not None else 0

        # Calculate approximate INR
        plan["price_inr_approx"] = round((plan.get("price_aed_calc") or 0) * aed_to_inr)

        if has_enough_data:
            filtered_candidates.append(plan)
        elif plan.get("product_type") == "esim_data_only":
            # Keep eSIM options even if slightly lower data as budget alternative
            filtered_candidates.append(plan)

    # If no plans fit the strict filter, fallback to all non-resident plans covering at least 7 days
    if not filtered_candidates:
        filtered_candidates = [
            p for p in all_plans 
            if ("resident" not in p.get("suitable_for", [])) and (p.get("validity_days", 0) >= 7)
        ]
        for p in filtered_candidates:
            if p.get("price_aed") is not None:
                p["price_aed_calc"] = p["price_aed"]
            elif p.get("price_usd_approx"):
                p["price_aed_calc"] = round(p["price_usd_approx"] * 3.6725, 2)
            else:
                p["price_aed_calc"] = 0
            p["price_inr_approx"] = round(p["price_aed_calc"] * aed_to_inr)

    # Sort candidates by confidence preference: high -> medium -> low, then price
    conf_order = {"high": 1, "medium": 2, "low": 3}
    filtered_candidates.sort(
        key=lambda x: (conf_order.get(x.get("confidence", "low"), 4), x.get("price_aed_calc", 999))
    )

    # Keep a compact payload of top matching candidates (max 6) for Gemini
    top_candidates = filtered_candidates[:6]

    # 3. Call Gemini with strict JSON instructions & rules
    lang_inst = "Respond with all textual explanations in English."
    if language == "ml":
        lang_inst = "Respond with 'why', 'warnings', and 'verify_message' in clear Malayalam (മലയാളം)."
    elif language == "hi":
        lang_inst = "Respond with 'why', 'warnings', and 'verify_message' in clear Hindi (हिन्दी)."

    system_prompt = f"""You are TravelGuard's UAE Telecom Advisor.
Recommend the best 1 to 3 plans ONLY from the provided filtered plans list.
NEVER invent a price, data amount, or plan name.
Prefer plans with confidence 'high', then 'medium'. If you recommend a 'low' confidence plan, state that figures may be out of date.
If trip duration exceeds 28 days, explain in warnings that user may need to recharge or buy another 28-day pack.

General Rules:
{json.dumps(meta.get('general_rules', []), ensure_ascii=False)}

{lang_inst}

You MUST respond with strictly valid JSON in this exact structure:
{{
  "best_pick_id": "<id of best plan>",
  "alternative_ids": ["<id>", ...],
  "why": "<clear 2-3 sentence explanation of why this plan fits the user's trip length and data need>",
  "total_cost_aed": <number>,
  "estimated_gb_needed": {estimated_gb_needed},
  "warnings": ["<warning or advice 1>", ...],
  "verify_message": "Prices change often. Confirm at the counter or in the operator app."
}}"""

    user_prompt = f"""Trip Details:
- Arrival City: {arrival_city}
- Stay Days: {days} days
- Estimated Data Needed: {estimated_gb_needed} GB
- User Type: {user_type}

Available Validated Plans:
{json.dumps(top_candidates, indent=2, ensure_ascii=False)}

Pick the single best plan and up to 2 alternatives from these exact plans."""

    ai_result = await ask_gemini(user_prompt, None, system_prompt)

    # Fallback if AI fails or returns empty
    if "error" in ai_result or not ai_result.get("best_pick_id"):
        best_plan = top_candidates[0] if top_candidates else {}
        alt_plans = top_candidates[1:3] if len(top_candidates) > 1 else []
        
        why_text = f"Recommended for a {days}-day stay with approximately {estimated_gb_needed} GB needed."
        if language == "ml":
            why_text = f"{days} ദിവസത്തെ യാത്രയ്ക്കും ഏകദേശം {estimated_gb_needed} GB ഡാറ്റയ്ക്കും അനുയോജ്യമായ പ്ലാൻ."
        elif language == "hi":
            why_text = f"{days} दिनों की यात्रा और लगभग {estimated_gb_needed} GB डेटा के लिए सबसे उपयुक्त प्लान।"

        ai_result = {
            "best_pick_id": best_plan.get("id"),
            "alternative_ids": [p.get("id") for p in alt_plans],
            "why": why_text,
            "total_cost_aed": best_plan.get("price_aed_calc", 0),
            "estimated_gb_needed": estimated_gb_needed,
            "warnings": [
                "Verify prices at the airport arrivals kiosk or inside the operator mobile app.",
                "UAE WhatsApp voice/video calls may be blocked; use local flexi minutes or Botim/GoChat."
            ],
            "verify_message": "Prices change often. Confirm at the counter or in the operator app."
        }

    # Format output items with details, AED, INR, confidence
    plan_map = {p["id"]: p for p in all_plans}
    
    def enrich_plan(p_id):
        p = plan_map.get(p_id)
        if not p:
            return None
        price_aed = p.get("price_aed")
        if price_aed is None and p.get("price_usd_approx"):
            price_aed = round(p["price_usd_approx"] * 3.6725, 2)
        price_inr = round((price_aed or 0) * aed_to_inr)

        data_display = "Unlimited" if p.get("unlimited_data") else f"{p.get('data_gb')} GB"
        mins_display = f"{p.get('flexi_minutes', 0)} Flexi Mins" if p.get("flexi_minutes") else "Data Only"

        return {
            "id": p.get("id"),
            "operator": p.get("operator"),
            "plan_name": p.get("plan_name"),
            "product_type": p.get("product_type"),
            "price_aed": price_aed,
            "price_inr_approx": price_inr,
            "data": data_display,
            "data_gb": p.get("data_gb"),
            "unlimited_data": bool(p.get("unlimited_data")),
            "validity": f"{p.get('validity_days')} Days",
            "validity_days": p.get("validity_days"),
            "minutes": mins_display,
            "confidence": p.get("confidence", "medium"),
            "perks": p.get("perks", []),
            "source_url": p.get("source_url", ""),
            "verify_note": p.get("verify_note", "")
        }

    best_pick = enrich_plan(ai_result.get("best_pick_id"))
    if not best_pick and top_candidates:
        best_pick = enrich_plan(top_candidates[0]["id"])

    alternatives = []
    for a_id in ai_result.get("alternative_ids", []):
        if a_id != (best_pick.get("id") if best_pick else None):
            enr = enrich_plan(a_id)
            if enr:
                alternatives.append(enr)

    # If alternatives empty, grab from top_candidates
    if not alternatives and len(top_candidates) > 1:
        for tc in top_candidates[1:3]:
            if tc["id"] != (best_pick.get("id") if best_pick else None):
                enr = enrich_plan(tc["id"])
                if enr:
                    alternatives.append(enr)

    # Build backward-compatible recommended_plans list for existing tests
    recommended_plans_list = []
    if best_pick:
        recommended_plans_list.append(best_pick)
    for alt in alternatives:
        recommended_plans_list.append(alt)

    airport_notes = meta.get("airport_notes", {})
    city_code = "DXB" if "dubai" in arrival_city.lower() else ("AUH" if "abu" in arrival_city.lower() else "SHJ")

    return {
        "arrival_city": arrival_city,
        "stay_days": days,
        "data_usage": data_usage,
        "estimated_gb_needed": estimated_gb_needed,
        "user_type": user_type,
        "meta": {
            "notice": meta.get("notice", "Plan prices and data allowances change often."),
            "last_checked": meta.get("last_checked", "2026-10-11"),
            "disclaimer": meta.get("disclaimer", "Guidance only. Verify with the operator before purchase.")
        },
        # Top-level notice and last_checked for frontend & test convenience
        "notice": meta.get("notice"),
        "last_checked": meta.get("last_checked"),
        "verification_notice": meta.get("notice"),
        "verify_message": "Prices change often. Confirm at the counter or in the operator app.",
        "best_pick": best_pick,
        "alternatives": alternatives,
        "recommended_plans": recommended_plans_list,
        "why": ai_result.get("why", ""),
        "warnings": ai_result.get("warnings", []),
        "airport_note": airport_notes.get(city_code, airport_notes.get("DXB", "")),
        "free_sim_info": {
            "title": "Free Tourist SIM / eSIM at Immigration (Reported)",
            "details": airport_notes.get("DXB", "")
        }
    }
