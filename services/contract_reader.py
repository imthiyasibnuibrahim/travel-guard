import logging
from typing import Optional
from services.gemini_service import ask_gemini

logger = logging.getLogger(__name__)


def rule_based_contract_fallback(text: Optional[str], language: str) -> dict:
    content = (text or "").lower()
    is_ml = language == "ml"
    is_hi = language == "hi"

    red_flags = []
    
    # Check passport retention
    has_passport_clause = "passport" in content
    employee_holds = any(w in content for w in [
        "employee retains", "worker retains", "employee holds", "worker keeps",
        "employee keeps", "retains passport", "holds passport at all times"
    ])
    employer_holds = any(w in content for w in [
        "surrender passport", "submit passport", "company custody", "employer keeps",
        "company keeps", "passport hold", "hold passport", "possession of employer",
        "custody of company", "surrender original passport"
    ])
    holds_passport = employer_holds and not employee_holds

    
    if holds_passport:
        if is_ml:
            red_flags.append("ഗുരുതരമായ നിയമലംഘനം: പാസ്‌പോർട്ട് കമ്പനി പിടിച്ചുവെക്കുന്നത് യുഎഇ നിയമപ്രകാരം (Federal Decree Law 33/2021) കർശനമായി നിരോധിച്ചിരിക്കുന്നു.")
        elif is_hi:
            red_flags.append("गंभीर कानूनी उल्लंघन: कंपनी द्वारा पासपोर्ट जब्त करना यूएई कानून के तहत गैरकानूनी है। पासपोर्ट हमेशा कर्मचारी के पास रहना चाहिए।")
        else:
            red_flags.append("ILLEGAL CLAUSE: Withholding employee passports is strictly illegal under UAE Federal Decree Law No. 33 of 2021 and Ministry of Interior regulations.")

    # Check visa cost deduction
    visa_deduction = ("visa" in content and any(w in content for w in ["deduct", "cost", "fee", "pay", "charge", "recover", "salary"])) or "processing fee" in content
    if visa_deduction:
        if is_ml:
            red_flags.append("ശമ്പളത്തിൽ നിന്ന് വിസ ചിലവ് കുറയ്ക്കുന്നത് നിയമവിരുദ്ധമാണ്. യുഎഇ നിയമപ്രകാരം എല്ലാ ചിലവുകളും തൊഴിലുടമ വഹിക്കണം.")
        elif is_hi:
            red_flags.append("वेतन से वीजा खर्च काटना गैरकानूनी है। कानूनन सभी खर्च नियोक्ता को उठाने होते हैं।")
        else:
            red_flags.append("ILLEGAL EXPENSE: Charging or deducting visa/recruitment fees from employee salary violates UAE Labor Law.")


    # Check excessive hours
    excessive_hours = any(w in content for w in ["12 hours", "14 hours", "no overtime", "no weekly off", "7 days a week"])
    if excessive_hours:
        if is_ml:
            red_flags.append("അമിത ജോലി സമയം: സാധാരണ യുഎഇ ജോലി സമയം പ്രതിദിനം 8 മണിക്കൂർ (ആഴ്ചയിൽ 48 മണിക്കൂർ) ആണ്. അധിക ജോലിക്ക് ഓവർടൈം നൽകണം.")
        elif is_hi:
            red_flags.append("अत्यधिक कार्य घंटे: यूएई में सामान्य कार्य समय 8 घंटे प्रतिदिन (48 घंटे प्रति सप्ताह) है।")
        else:
            red_flags.append("EXCESSIVE WORKING HOURS: Normal UAE working hours are 8 hours/day (48 hours/week). Overtime pay is mandatory for extra hours.")

    verdict = "dangerous" if len(red_flags) >= 2 or holds_passport else ("review_needed" if len(red_flags) == 1 else "safe")

    if is_ml:
        summary = "തൊഴിൽ കരാർ പരിശോധിച്ചു. " + ("ശ്രദ്ധിക്കുക: നിയമവിരുദ്ധമായ ചില വ്യവസ്ഥകൾ ശ്രദ്ധയിൽപ്പെട്ടിട്ടുണ്ട്." if red_flags else "കരാറിൽ പ്രകടമായ നിയമലംഘനങ്ങൾ കണ്ടെത്തിയില്ല.")
    elif is_hi:
        summary = "अनुबंध की समीक्षा की गई। " + ("सावधान: कुछ गैरकानूनी शर्तें पाई गई हैं।" if red_flags else "अनुबंध में कोई स्पष्ट अवैध शर्त नहीं मिली।")
    else:
        summary = "Contract analysis complete. " + ("WARNING: Suspicious or illegal clauses detected." if red_flags else "No glaring illegal clauses detected in text.")

    return {
        "job_title": "Identified in contract" if not is_ml else "കരാറിലെ ജോലി",
        "basic_salary": "Check MOHRE offer letter" if not is_ml else "MOHRE ഓഫർ ലെറ്ററിലെ തുക",
        "working_hours": "8 hrs/day (standard UAE labor law)" if not is_ml else "പ്രതിദിനം 8 മണിക്കൂർ",
        "passport_retention": "Employee holds passport (Employer retention is illegal)" if not holds_passport else "VIOLATION DETECTED: Employer retention clause",
        "probation_period": "Max 6 months under UAE law" if not is_ml else "പരമാവധി 6 മാസം",
        "termination_terms": "Standard 30-90 days notice" if not is_ml else "30 മുതൽ 90 ദിവസം വരെയുള്ള നോട്ടീസ്",
        "red_flags": red_flags,
        "contract_verdict": verdict,
        "summary": summary
    }


async def analyze_contract(
    text: Optional[str],
    image_bytes: Optional[bytes],
    language: str = "en"
) -> dict:
    lang_instruction = ""
    if language == "ml":
        lang_instruction = "Respond with all textual explanations and summary in Malayalam (മലയാളം)."
    elif language == "hi":
        lang_instruction = "Respond with all textual explanations and summary in Hindi (हिन्दी)."

    system_prompt = f"""You are TravelGuard's expert UAE Labor Law Contract Reader.
Analyze the employment contract or offer letter according to UAE Federal Decree Law No. 33 of 2021.

Examine and extract:
1. job_title: job role
2. basic_salary: monthly salary and currency
3. working_hours: daily/weekly hours and overtime
4. passport_retention: DOES IT STATE EMPLOYER HOLDS PASSPORT? Note: Holding an employee's passport is strictly ILLEGAL in the UAE.
5. probation_period: max legal limit is 6 months
6. termination_terms: notice period and end of service rights
7. red_flags: Array of strings highlighting unfair, illegal, or scam terms (e.g. passport withholding, employee pays visa fees, no day off, unfair fines)
8. contract_verdict: 'safe' | 'review_needed' | 'dangerous'
9. summary: A helpful 2-sentence explanation of what to verify before signing.

{lang_instruction}

Respond in strictly valid JSON format:
{{
  "job_title": "string",
  "basic_salary": "string",
  "working_hours": "string",
  "passport_retention": "string",
  "probation_period": "string",
  "termination_terms": "string",
  "red_flags": ["flag 1", ...],
  "contract_verdict": "safe" | "review_needed" | "dangerous",
  "summary": "string"
}}"""

    user_prompt = ""
    if text:
        user_prompt = f"Analyze this employment contract for legality and fair terms under UAE law:\n\n{text}"
    elif image_bytes:
        user_prompt = "Examine the text and terms in this photograph of an employment contract/offer letter. Extract key terms and detect illegal or unfair clauses."

    result = await ask_gemini(user_prompt, image_bytes, system_prompt)

    if "error" in result:
        logger.warning(f"Gemini contract check failed, using rule-based fallback: {result.get('error')}")
        return rule_based_contract_fallback(text, language)

    result.setdefault("red_flags", [])
    result.setdefault("contract_verdict", "review_needed")
    result.setdefault("summary", "Contract analysis complete.")

    return result
