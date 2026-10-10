import logging
from typing import Optional
from services.gemini_service import ask_gemini

logger = logging.getLogger(__name__)


def rule_based_offer_fallback(text: Optional[str], language: str, emigration_rules: dict) -> dict:
    """Intelligent rule-based fallback grounded in emigration_rules.json."""
    content = (text or "").lower()
    is_ml = language == "ml"
    
    red_flags = []
    what_to_verify = []
    safe_next_steps = []
    
    # 1. Asking money upfront
    money_words = ["fee", "fees", "processing fee", "upfront", "₹", "rs", "inr", "rupee", "deposit", "advance", "lakh", "pay ", "payment", "personal account"]
    if any(w in content for w in money_words):
        red_flags.append(
            "മുൻകൂർ പണം ആവശ്യപ്പെടുന്നു (വിസ/പ്രോസസ്സിംഗ് ഫീസ് നിയമവിരുദ്ധമാണ്)" if is_ml
            else "Asking for money/fees upfront (Employers must bear all visa and recruitment costs under UAE & Indian law)"
        )
    
    # 2. Tourist visa for work
    visa_words = ["tourist", "visit visa", "convert to work", "free visa", "azad"]
    if any(w in content for w in visa_words):
        red_flags.append(
            "ജോലിക്കായി സന്ദർശക (ടൂറിസ്റ്റ്) വിസ വാഗ്ദാനം ചെയ്യുന്നു (ഇത് കർശനമായി നിരോധിച്ചിരിക്കുന്നു)" if is_ml
            else "Offering employment on a tourist/visit visa (Illegal in UAE; requires official Employment Visa)"
        )
    
    # 3. High/unrealistic salary
    salary_words = ["15,000", "15000", "20,000", "20000", "guaranteed salary", "high salary"]
    if any(w in content for w in salary_words):
        red_flags.append(
            "യാഥാർത്ഥ്യത്തിന് നിരക്കാത്ത അമിത ശമ്പള വാഗ്ദാനം" if is_ml
            else "Unrealistically high salary promise for the stated role"
        )
    
    # 4. Pressure tactics
    pressure_words = ["today", "tonight", "urgent", "last 2 seats", "immediately", "hurry", "exclusive", "don't tell"]
    if any(w in content for w in pressure_words):
        red_flags.append(
            "ഉടൻ പണം അടയ്ക്കാനോ തീരുമാനമെടുക്കാനോ ഉള്ള സമ്മർദ്ദം" if is_ml
            else "High pressure tactics to decide quickly or keep the offer secret"
        )
    
    # 5. WhatsApp only / Personal contact
    wa_words = ["whatsapp only", "dm me", "+971 50", "+971 55", "personal account", "personal number"]
    if any(w in content for w in wa_words):
        red_flags.append(
            "വ്യക്തിഗത വാട്ട്‌സ്ആപ്പ് വഴി മാത്രം ബന്ധപ്പെടാൻ നിർദ്ദേശിക്കുന്നു (ഔദ്യോഗിക ഇമെയിലോ ഫോണോ ഇല്ല)" if is_ml
            else "Contact only via personal WhatsApp/mobile, no official company email domain or landline"
        )
    
    # 6. Unverifiable company
    if not any(w in content for w in ["license", "mohre", "attested", "trade license"]):
        what_to_verify.append(
            "കമ്പനിയുടെ യുഎഇ ട്രേഡ് ലൈസൻസും MOHRE രജിസ്ട്രേഷനും പരിശോധിക്കുക" if is_ml
            else "Verify company trade license number and UAE MOHRE establishment card"
        )
    
    what_to_verify.append(
        "റിക്രൂട്ടിംഗ് ഏജന്റിന് കേന്ദ്ര വിദേശകാര്യ മന്ത്രാലയത്തിന്റെ (MEA) രജിസ്ട്രേഷൻ ഉണ്ടോയെന്ന് eMigrate പോർട്ടലിൽ പരിശോധിക്കുക" if is_ml
        else "Check if the recruitment agent holds a valid MEA license on eMigrate portal (emigrate.gov.in)"
    )
    what_to_verify.append(
        "എംബസി സാക്ഷ്യപ്പെടുത്തിയ ഔദ്യോഗിക തൊഴിൽ ഓഫർ ലെറ്റർ ആവശ്യപ്പെടുക" if is_ml
        else "Demand an official, verifiable employment contract attested by the Indian Embassy/Consulate"
    )

    safe_next_steps.append(
        "യാതൊരു കാരണവശാലും വ്യക്തിഗത അക്കൗണ്ടുകളിലേക്ക് പണം കൈമാറരുത്" if is_ml
        else "Do NOT transfer any money or processing fees to any personal account"
    )
    safe_next_steps.append(
        "സഹായത്തിനായി നോർക്ക-റൂട്ട്സ് (NORKA-Roots) ഹെൽപ്പ്‌ലൈനിൽ (1800-425-3939) വിളിക്കുക" if is_ml
        else "Contact NORKA-Roots 24/7 helpline for Kerala expatriates at 1800-425-3939"
    )
    safe_next_steps.append(
        "eMigrate ഹെൽപ്പ്‌ഡെസ്ക് നമ്പറുമായി (1800-11-3090) ബന്ധപ്പെട്ട് നിയമസാധുത ഉറപ്പാക്കുക" if is_ml
        else "Call the official eMigrate Pravasi Bharatiya Sahayata Kendra helpline at 1800-11-3090"
    )

    # Calculate risk score
    flag_count = len(red_flags)
    if flag_count >= 3:
        risk_score = min(95, 60 + flag_count * 10)
        risk_level = "high"
        summary = (
            "അതീവ ഗുരുതരമായ തട്ടിപ്പ് സാധ്യത! ഈ ഓഫറിൽ ഒന്നിലധികം വ്യാജ സൂചനകൾ കണ്ടെത്തിയിട്ടുണ്ട്. പണം നൽകുകയോ യാത്ര ചെയ്യുകയോ ചെയ്യരുത്." if is_ml
            else "CRITICAL FRAUD RISK! Multiple severe scam indicators detected. Do not pay any money or travel on this offer."
        )
    elif flag_count >= 1:
        risk_score = 45 + flag_count * 15
        risk_level = "medium"
        summary = (
            "മുന്നറിയിപ്പ്: സംശയാസ്പദമായ ചില ഘടകങ്ങൾ ശ്രദ്ധയിൽപ്പെട്ടിട്ടുണ്ട്. ഔദ്യോഗിക രേഖകൾ പൂർണ്ണമായി പരിശോധിച്ച ശേഷം മാത്രം മുന്നോട്ട് പോകുക." if is_ml
            else "Moderate risk detected: Offer contains suspicious terms. Verify all credentials thoroughly before proceeding."
        )
    else:
        risk_score = 25
        risk_level = "low"
        summary = (
            "പ്രാഥമികമായി വ്യക്തമായ തട്ടിപ്പ് സൂചനകൾ കാണുന്നില്ലെങ്കിലും, ജോലിക്ക് പോകുന്നതിന് മുൻപ് കരാറും വിസയും ഔദ്യോഗികമായി പരിശോധിക്കുക." if is_ml
            else "No obvious red flags detected in the text, but always verify contract with eMigrate and UAE MOHRE before departure."
        )
        safe_next_steps.append(
            "യുഎഇ ലേബർ കോൺട്രാക്റ്റ് mohre.gov.ae ൽ ലോഗിൻ ചെയ്ത് നേരിട്ട് പരിശോധിക്കുക" if is_ml
            else "Verify labor contract directly on mohre.gov.ae"
        )

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "red_flags": red_flags,
        "what_to_verify": what_to_verify,
        "safe_next_steps": safe_next_steps,
        "summary": summary
    }


async def analyze_offer(
    text: Optional[str],
    image_bytes: Optional[bytes],
    language: str,
    emigration_rules: dict
) -> dict:
    """Analyze a job offer or agent message for scam indicators."""
    
    lang_instruction = ""
    if language == "ml":
        lang_instruction = "Respond with all text fields in Malayalam (മലയാളം) language."
    
    rules_context = ""
    if emigration_rules:
        import json
        rules_context = f"""\n\nUse these official emigration rules as ground truth for your analysis:
{json.dumps(emigration_rules, indent=2, ensure_ascii=False)}"""
    
    system_prompt = f"""You are TravelGuard, an expert at detecting fraudulent job offers, 
scam recruitment messages, and unsafe migration schemes targeting workers from India 
(especially Kerala) going to Gulf countries (UAE, Saudi Arabia, Qatar, Oman, Bahrain, Kuwait).

You MUST check for these red flags:
- Asking money upfront (visa fees, processing fees, etc.)
- No verifiable company name or physical address
- Tourist visa being offered for employment
- Unrealistic salary promises
- Pressure to decide quickly
- Personal WhatsApp-only contact (no official email/phone)
- Unofficial or unregistered recruitment agent
- No mention of employment contract
- Vague job description
- Promises that sound too good to be true
{rules_context}

{lang_instruction}

You MUST respond with ONLY valid JSON in this exact format:
{{
  "risk_score": <number 0-100>,
  "risk_level": "low" | "medium" | "high",
  "red_flags": ["flag1", "flag2", ...],
  "what_to_verify": ["item1", "item2", ...],
  "safe_next_steps": ["step1", "step2", ...],
  "summary": "Brief summary of the analysis"
}}"""

    user_prompt = ""
    if text:
        user_prompt = f"Analyze this job offer / recruitment message for safety:\n\n{text}"
    elif image_bytes:
        user_prompt = "Analyze the text in this image. It's a job offer or recruitment message. Check it for scam indicators and safety concerns."
    
    result = await ask_gemini(user_prompt, image_bytes, system_prompt)
    
    # If Gemini returns an error or empty result, use intelligent rule-based fallback
    if "error" in result:
        logger.warning(f"Gemini call failed ({result.get('error')}), using rule-based analysis fallback")
        return rule_based_offer_fallback(text, language, emigration_rules)
    
    # Ensure required fields exist
    result.setdefault("risk_score", 50)
    result.setdefault("risk_level", "medium")
    result.setdefault("red_flags", [])
    result.setdefault("what_to_verify", [])
    result.setdefault("safe_next_steps", [])
    result.setdefault("summary", "Analysis complete.")
    
    return result

