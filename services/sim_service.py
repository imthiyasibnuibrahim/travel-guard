import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_sim_recommendations(
    arrival_city: str = "Dubai",
    stay_days: int = 7,
    data_usage: str = "medium",  # light, medium, heavy
    user_type: str = "visitor",  # visitor or resident
    language: str = "en"
) -> dict:
    try:
        with open("data/sim_plans.json", "r", encoding="utf-8") as f:
            sim_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load sim_plans.json: {e}")
        sim_data = {}

    operators = sim_data.get("operators", [])
    last_checked = sim_data.get("last_checked", "2026-10-10")
    airport_free_info = sim_data.get("airport_free_sim_info", {})
    buying_tips = sim_data.get("buying_tips", [])

    recommended_plans = []

    for op in operators:
        op_name = op.get("name")
        for plan in op.get("plans", []):
            plan_name = plan.get("plan_name", "").lower()
            rec_for = plan.get("recommended_for", "").lower()

            is_resident_plan = "resident" in plan_name or "resident" in rec_for
            if user_type == "visitor" and is_resident_plan:
                continue
            if user_type == "resident" and not is_resident_plan and stay_days > 30:
                continue

            # Tag match score
            score = 1
            if data_usage == "heavy" and ("unlimited" in plan_name or "20 gb" in plan.get("data", "").lower() or "21 gb" in plan.get("data", "").lower()):
                score += 3
            elif data_usage == "light" and "starter" in plan_name or "explorer" in plan_name:
                score += 3
            elif data_usage == "medium":
                score += 2

            recommended_plans.append({
                "operator": op_name,
                "badge": op.get("badge"),
                "plan_name": plan.get("plan_name"),
                "price_aed": plan.get("price_aed"),
                "price_inr_approx": round(plan.get("price_aed", 0) * 26.38),
                "data_allowance": plan.get("data"),
                "validity": plan.get("validity"),
                "recommended_for": plan.get("recommended_for"),
                "notes": plan.get("notes"),
                "counter_locations": op.get("counter_locations"),
                "official_url": op.get("official_url"),
                "score": score
            })

    # Sort by score descending
    recommended_plans.sort(key=lambda x: x["score"], reverse=True)

    verified_notes = {
        "en": f"Official prices last verified on {last_checked} from TDRA / operator portals. Promos change periodically; always verify rates at the official airport kiosk counter before signing.",
        "ml": f"ഔദ്യോഗിക നിരക്കുകൾ {last_checked} തീയതിയിൽ പരിശോധിച്ചതാണ്. വാങ്ങുന്നതിന് മുൻപ് എയർപോർട്ടിലെ കൗണ്ടറിൽ നിരക്ക് നേരിട്ട് പരിശോധിക്കുക.",
        "hi": f"आधिकारिक दरें {last_checked} को जांची गई थीं। एयरपोर्ट काउंटर पर खरीदारी से पहले कीमत की पुष्टि अवश्य करें।"
    }

    return {
        "arrival_city": arrival_city,
        "stay_days": stay_days,
        "data_usage": data_usage,
        "user_type": user_type,
        "last_checked": last_checked,
        "verification_notice": verified_notes.get(language, verified_notes["en"]),
        "free_sim_info": {
            "title": airport_free_info.get(f"title_{language}", airport_free_info.get("title_en", "Free Tourist SIM")),
            "details": airport_free_info.get(f"details_{language}", airport_free_info.get("details_en", ""))
        },
        "recommended_plans": recommended_plans[:4],
        "buying_tips": buying_tips
    }
