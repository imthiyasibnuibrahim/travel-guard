import logging
from typing import Optional
from services.gemini_service import ask_gemini

logger = logging.getLogger(__name__)


def rule_based_offer_fallback(text: Optional[str], language: str, emigration_rules: dict) -> dict:
    """Intelligent rule-based fallback grounded in emigration_rules.json."""
    content = (text or "").lower()
    is_ml = language == "ml"
    is_hi = language == "hi"
    
    red_flags = []
    what_to_verify = []
    safe_next_steps = []
    
    # 1. Asking money upfront
    money_words = ["fee", "fees", "processing fee", "upfront", "₹", "rs", "inr", "rupee", "deposit", "advance", "lakh", "pay ", "payment", "personal account"]
    if any(w in content for w in money_words):
        if is_ml:
            flag = "മുൻകൂർ പണം ആവശ്യപ്പെടുന്നു (വിസ/പ്രോസസ്സിംഗ് ഫീസ് നിയമവിരുദ്ധമാണ്)"
        elif is_hi:
            flag = "अग्रिम शुल्क की मांग (वीजा या भर्ती शुल्क मांगना कानूनन अवैध है)"
        else:
            flag = "Asking for money/fees upfront (Employers must bear all visa and recruitment costs under UAE & Indian law)"
        red_flags.append(flag)
    
    # 2. Tourist visa for work
    visa_words = ["tourist", "visit visa", "convert to work", "free visa", "azad"]
    if any(w in content for w in visa_words):
        if is_ml:
            flag = "ജോലിക്കായി സന്ദർശക (ടൂറിസ്റ്റ്) വിസ വാഗ്ദാനം ചെയ്യുന്നു (ഇത് കർശനമായി നിരോധിച്ചിരിക്കുന്നു)"
        elif is_hi:
            flag = "काम के लिए टूरिस्ट/विजिट वीजा की पेशकश (यूएई कानून के तहत यह सख्त अवैध है)"
        else:
            flag = "Offering employment on a tourist/visit visa (Illegal in UAE; requires official Employment Visa)"
        red_flags.append(flag)
    
    # 3. High/unrealistic salary
    salary_words = ["15,000", "15000", "20,000", "20000", "guaranteed salary", "high salary"]
    if any(w in content for w in salary_words):
        if is_ml:
            flag = "യാഥാർത്ഥ്യത്തിന് നിരക്കാത്ത അമിത ശമ്പള വാഗ്ദാനം"
        elif is_hi:
            flag = "अवास्तविक और बहुत अधिक वेतन का झांसा"
        else:
            flag = "Unrealistically high salary promise for the stated role"
        red_flags.append(flag)
    
    # 4. Pressure tactics
    pressure_words = ["today", "tonight", "urgent", "last 2 seats", "immediately", "hurry", "exclusive", "don't tell"]
    if any(w in content for w in pressure_words):
        if is_ml:
            flag = "ഉടൻ പണം അടയ്ക്കാനോ തീരുമാനമെടുക്കാനോ ഉള്ള സമ്മർദ്ദം"
        elif is_hi:
            flag = "जल्दबाजी में निर्णय लेने या तुरंत पैसे भेजने का दबाव"
        else:
            flag = "High pressure tactics to decide quickly or keep the offer secret"
        red_flags.append(flag)
    
    # 5. WhatsApp only / Personal contact
    wa_words = ["whatsapp only", "dm me", "+971 50", "+971 55", "personal account", "personal number"]
    if any(w in content for w in wa_words):
        if is_ml:
            flag = "വ്യക്തിഗത വാട്ട്‌സ്ആപ്പ് വഴി മാത്രം ബന്ധപ്പെടാൻ നിർദ്ദേശിക്കുന്നു (ഔദ്യോഗിക ഇമെയിലോ ഫോണോ ഇല്ല)"
        elif is_hi:
            flag = "केवल व्यक्तिगत व्हाट्सएप या मोबाइल पर संपर्क (कोई आधिकारिक ईमेल या पता नहीं)"
        else:
            flag = "Contact only via personal WhatsApp/mobile, no official company email domain or landline"
        red_flags.append(flag)
    
    # 6. What to verify
    if not any(w in content for w in ["license", "mohre", "attested", "trade license"]):
        what_to_verify.append(
            "കമ്പനിയുടെ യുഎഇ ട്രേഡ് ലൈസൻസും MOHRE രജിസ്ട്രേഷനും പരിശോധിക്കുക" if is_ml
            else ("कंपनी का यूएई ट्रेड लाइसेंस और MOHRE पंजीकरण जांचें" if is_hi
            else "Verify company trade license number and UAE MOHRE establishment card")
        )
    
    what_to_verify.append(
        "റിക്രൂട്ടിംഗ് ഏജന്റിന് കേന്ദ്ര വിദേശകാര്യ മന്ത്രാലയത്തിന്റെ (MEA) രജിസ്ട്രേഷൻ ഉണ്ടോയെന്ന് eMigrate പോർട്ടലിൽ പരിശോധിക്കുക" if is_ml
        else ("जांचें कि भर्ती एजेंट के पास eMigrate पोर्टल पर वैध MEA लाइसेंस है या नहीं" if is_hi
        else "Check if the recruitment agent holds a valid MEA license on eMigrate portal (emigrate.gov.in)")
    )
    what_to_verify.append(
        "എംബസി സാക്ഷ്യപ്പെടുത്തിയ ഔദ്യോഗിക തൊഴിൽ ഓഫർ ലെറ്റർ ആവശ്യപ്പെടുക" if is_ml
        else ("भारतीय दूतावास द्वारा सत्यापित आधिकारिक रोजगार अनुबंध की मांग करें" if is_hi
        else "Demand an official, verifiable employment contract attested by the Indian Embassy/Consulate")
    )

    safe_next_steps.append(
        "യാതൊരു കാരണവശാലും വ്യക്തിഗത അക്കൗണ്ടുകളിലേക്ക് പണം കൈമാറരുത്" if is_ml
        else ("किसी भी व्यक्तिगत खाते में पैसे या प्रोसेसिंग फीस बिल्कुल न भेजें" if is_hi
        else "Do NOT transfer any money or processing fees to any personal account")
    )
    safe_next_steps.append(
        "സഹായത്തിനായി നോർക്ക-റൂട്ട്സ് (NORKA-Roots) ഹെൽപ്പ്‌ലൈനിൽ (1800-425-3939) വിളിക്കുക" if is_ml
        else ("नॉर्का-रूट्स (1800-425-3939) या प्रवासी हेल्पलाइन से संपर्क करें" if is_hi
        else "Contact NORKA-Roots 24/7 helpline for expatriates at 1800-425-3939")
    )
    safe_next_steps.append(
        "eMigrate ഹെൽപ്പ്‌ഡെസ്ക് നമ്പറുമായി (1800-11-3090) ബന്ധപ്പെട്ട് നിയമസാധുത ഉറപ്പാക്കുക" if is_ml
        else ("आधिकारिक eMigrate हेल्पलाइन (1800-11-3090) पर कॉल करके पुष्टि करें" if is_hi
        else "Call the official eMigrate Pravasi Bharatiya Sahayata Kendra helpline at 1800-11-3090")
    )

    # Calculate risk score
    flag_count = len(red_flags)
    if flag_count >= 3:
        risk_score = min(95, 60 + flag_count * 10)
        risk_level = "high"
        summary = (
            "അതീവ ഗുരുതരമായ തട്ടിപ്പ് സാധ്യത! ഈ ഓഫറിൽ ഒന്നിലധികം വ്യാജ സൂചനകൾ കണ്ടെത്തിയിട്ടുണ്ട്. പണം നൽകുകയോ യാത്ര ചെയ്യുകയോ ചെയ്യരുത്." if is_ml
            else ("अत्यधिक जोखिम / संभावित धोखाधड़ी! इस ऑफर में कई संदिग्ध संकेत मिले हैं। पैसे बिल्कुल न दें।" if is_hi
            else "CRITICAL FRAUD RISK! Multiple severe scam indicators detected. Do not pay any money or travel on this offer.")
        )
    elif flag_count >= 1:
        risk_score = 45 + flag_count * 15
        risk_level = "medium"
        summary = (
            "മുന്നറിയിപ്പ്: സംശയാസ്പദമായ ചില ഘടകങ്ങൾ ശ്രദ്ധയിൽപ്പെട്ടിട്ടുണ്ട്. ഔദ്യോഗിക രേഖകൾ പൂർണ്ണമായി പരിശോധിച്ച ശേഷം മാത്രം മുന്നോട്ട് പോകുക." if is_ml
            else ("मध्यम जोखिम: इस प्रस्ताव में कुछ संदिग्ध नियम शामिल हैं। आगे बढ़ने से पहले सभी प्रमाणपत्रों की जांच करें।" if is_hi
            else "Moderate risk detected: Offer contains suspicious terms. Verify all credentials thoroughly before proceeding.")
        )
    else:
        risk_score = 25
        risk_level = "low"
        summary = (
            "പ്രാഥമികമായി വ്യക്തമായ തട്ടിപ്പ് സൂചനകൾ കാണുന്നില്ലെങ്കിലും, ജോലിക്ക് പോകുന്നതിന് മുൻപ് കരാറും വിസയും ഔദ്യോഗികമായി പരിശോധിക്കുക." if is_ml
            else ("कोई स्पष्ट लाल झंडा नहीं दिखा, लेकिन यात्रा से पहले ई-माइग्रेट पर अनुबंध की पुष्टि अवश्य करें।" if is_hi
            else "No obvious red flags detected in the text, but always verify contract with eMigrate and UAE MOHRE before departure.")
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
    elif language == "hi":
        lang_instruction = "Respond with all text fields in Hindi (हिन्दी) language."

    
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

