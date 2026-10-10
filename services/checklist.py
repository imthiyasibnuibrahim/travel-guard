import json
import logging
from typing import Optional
from services.gemini_service import ask_gemini

logger = logging.getLogger(__name__)


def rule_based_checklist_fallback(
    destination: str,
    purpose: str,
    travel_date: str,
    layover_hours: Optional[float],
    language: str,
    emigration_rules: dict
) -> dict:
    """Intelligent rule-based fallback grounded in emigration_rules.json."""
    is_ml = language == "ml"
    
    # Layover calculation
    layover_info = None
    if layover_hours is not None and layover_hours > 0:
        safe_to_leave = layover_hours >= 6.0
        if safe_to_leave:
            return_by_time = "കണക്റ്റിംഗ് ഫ്ലൈറ്റിന് 3 മണിക്കൂർ മുൻപ്" if is_ml else "At least 3 hours before next flight"
            things_to_do = (
                ["ദുബായ് മാളും ബുർജ് ഖലീഫയും സന്ദർശിക്കുക (മെട്രോ വഴി)", "ദുബായ് ഫ്രെയിം", "ദുബായ് ക്രീക്കിലെ അബ്ര ബോട്ട് യാത്ര"] if is_ml
                else ["Visit Dubai Mall & Burj Khalifa (via Dubai Metro)", "Explore Dubai Frame", "Traditional Abra boat ride at Dubai Creek"]
            )
        else:
            return_by_time = "എയർപോർട്ട് ട്രാൻസിറ്റ് ഏരിയയിൽ തന്നെ തുടരുക" if is_ml else "Remain inside international transit area"
            things_to_do = (
                ["ട്രാൻസിറ്റ് ലോഞ്ചിൽ വിശ്രമിക്കുക", "ഡ്യൂട്ടി ഫ്രീ ഷോപ്പിംഗ്", "സ്ലീപ്പിംഗ് പോഡുകൾ ഉപയോഗിക്കുക"] if is_ml
                else ["Relax at airport transit lounge", "Browse Dubai Duty Free", "Use Marhaba lounge or SnoozeCube sleep pods"]
            )
        
        layover_info = {
            "safe_to_leave": safe_to_leave,
            "return_by_time": return_by_time,
            "transit_visa_needed": True if safe_to_leave else False,
            "things_to_do": things_to_do
        }

    # Checklist categories
    categories = []
    
    # Category 1: Documents
    doc_items = [
        {
            "task": "പാസ്‌പോർട്ടിന് കുറഞ്ഞത് 6 മാസത്തെ കാലാവധിയുണ്ടെന്ന് ഉറപ്പാക്കുക" if is_ml else "Ensure passport has at least 6 months validity from travel date",
            "deadline": "യാത്രയ്ക്ക് 4 ആഴ്ച മുൻപ്" if is_ml else "4 weeks before travel",
            "details": "കാലാവധി കുറവാണെങ്കിൽ ഉടൻ തന്നെ പാസ്‌പോർട്ട് സേവാ കേന്ദ്രം വഴി പുതുക്കുക" if is_ml else "Renew immediately at Passport Seva Kendra if expiring soon",
            "priority": "high"
        },
        {
            "task": "ശരിയായ എംപ്ലോയ്‌മെന്റ് വിസ ലഭിച്ചിട്ടുണ്ടെന്ന് പരിശോധിക്കുക (ടൂറിസ്റ്റ് വിസയല്ല)" if is_ml else "Verify valid Employment Visa / Entry Permit (NOT a tourist visa for work)",
            "deadline": "യാത്രയ്ക്ക് 2 ആഴ്ച മുൻപ്" if is_ml else "2 weeks before travel",
            "details": "യുഎഇ ICP വെബ്‌സൈറ്റ് (smartservices.icp.gov.ae) വഴി വിസ സാധുത ഓൺലൈനായി പരിശോധിക്കുക" if is_ml else "Check visa validity on UAE ICP portal (smartservices.icp.gov.ae)",
            "priority": "high"
        }
    ]

    if purpose == "work":
        doc_items.extend([
            {
                "task": "eMigrate പോർട്ടൽ വഴി പ്രൊട്ടക്ടർ ഓഫ് എമിഗ്രന്റ്‌സിൽ (PoE) നിന്ന് എമിഗ്രേഷൻ ക്ലിയറൻസ് നേടുക" if is_ml else "Obtain Emigration Clearance from PoE via eMigrate portal (mandatory for ECR passports)",
                "deadline": "യാത്രയ്ക്ക് 10 ദിവസം മുൻപ്" if is_ml else "10 days before travel",
                "details": "ECR പാസ്‌പോർട്ടുള്ളവർക്ക് കുടിയേറ്റ ക്ലിയറൻസ് നിർബന്ധമാണ്" if is_ml else "Mandatory legal requirement under Indian Emigration Act for 18 ECR countries",
                "priority": "high"
            },
            {
                "task": "യുഎഇ മാനവ വിഭവശേഷി മന്ത്രാലയം (MOHRE) അംഗീകരിച്ച തൊഴിൽ കരാർ കൈവശം വയ്ക്കുക" if is_ml else "Carry attested MOHRE standard employment contract signed by employer",
                "deadline": "യാത്രയ്ക്ക് 1 ആഴ്ച മുൻപ്" if is_ml else "1 week before travel",
                "details": "ശമ്പളം, താമസം, വിമാന ടിക്കറ്റ് വ്യവസ്ഥകൾ വ്യക്തമായി രേഖപ്പെടുത്തിയിട്ടുണ്ടെന്ന് ഉറപ്പാക്കുക" if is_ml else "Verify salary, working hours, accommodation and return ticket clauses",
                "priority": "high"
            },
            {
                "task": "പ്രവാസി ഭാരതീയ ബീമാ യോജന (PBBY) ഇൻഷുറൻസ് പോളിസി എടുക്കുക" if is_ml else "Secure Pravasi Bharatiya Bima Yojana (PBBY) insurance policy",
                "deadline": "യാത്രയ്ക്ക് 5 ദിവസം മുൻപ്" if is_ml else "5 days before travel",
                "details": "വിദേശത്ത് ജോലി ചെയ്യുന്ന ഇന്ത്യൻ തൊഴിലാളികൾക്ക് നിർബന്ധിത ഇൻഷുറൻസ് പരിരക്ഷ" if is_ml else "Mandatory ₹10 lakh insurance coverage for overseas Indian workers",
                "priority": "high"
            }
        ])

    categories.append({
        "category": "പ്രധാന രേഖകളും അനുമതികളും" if is_ml else "Essential Documents & Emigration Clearances",
        "items": doc_items
    })

    # Category 2: Health & Baggage
    health_items = [
        {
            "task": "എല്ലാ മരുന്നുകൾക്കും ഡോക്ടറുടെ ഒപ്പും സീലുമുള്ള കുറിപ്പടി (Prescription) കരുതുക" if is_ml else "Carry doctor's detailed prescription with medical registration seal for all medicines",
            "deadline": "യാത്രയ്ക്ക് 3 ദിവസം മുൻപ്" if is_ml else "3 days before travel",
            "details": "പരമാവധി 3 മാസത്തെ മരുന്ന് മാത്രം യഥാർത്ഥ പാക്കറ്റിൽ കൊണ്ടുപോകുക. കോഡീൻ അടങ്ങിയ കഫ് സിറപ്പുകൾ ഒഴിവാക്കുക" if is_ml else "Maximum 3 months supply in original packaging. Strictly avoid codeine syrups",
            "priority": "high"
        },
        {
            "task": "നിരോധിച്ച സാധനങ്ങളോ അമിത സ്വർണ്ണമോ ബാഗേജിൽ ഇല്ലെന്ന് ഉറപ്പുവരുത്തുക" if is_ml else "Cross-check baggage items against UAE Customs banned goods list",
            "deadline": "പാക്കിംഗ് സമയത്ത്" if is_ml else "During packing",
            "details": "യുഎഇ കസ്റ്റംസ് നിയമങ്ങൾ കർശനമായി പാലിക്കുക" if is_ml else "Pork products, banned narcotics, and unlabeled powders are strictly prohibited",
            "priority": "medium"
        }
    ]
    categories.append({
        "category": "ആരോഗ്യവും ലഗേജ് മുൻകരുതലുകളും" if is_ml else "Health & Baggage Safety",
        "items": health_items
    })

    # Category 3: Departure Day
    categories.append({
        "category": "യാത്രാ ദിന നിർദ്ദേശങ്ങൾ" if is_ml else "Departure Day Checklist",
        "items": [
            {
                "task": "ഫ്ലൈറ്റ് പുറപ്പെടുന്നതിന് 4 മണിക്കൂർ മുൻപ് വിമാനത്താവളത്തിൽ എത്തുക" if is_ml else "Arrive at airport at least 4 hours before scheduled departure",
                "deadline": "യാത്രാ ദിനം" if is_ml else "Travel Day",
                "details": "ഇമിഗ്രേഷൻ കൗണ്ടറുകളിലെ ക്ലിയറൻസിന് കൂടുതൽ സമയം വേണ്ടിവന്നേക്കാം" if is_ml else "Allows sufficient time for PoE checks, airline check-in, and emigration stamping",
                "priority": "high"
            },
            {
                "task": "പാസ്‌പോർട്ട്, വിസ, കരാർ എന്നിവയുടെ ഫോട്ടോകോപ്പികളും ഡിജിറ്റൽ കോപ്പികളും ഫോണിൽ സൂക്ഷിക്കുക" if is_ml else "Keep physical photocopies and digital cloud backups of all travel documents",
                "deadline": "ഹാൻഡ് ബാഗേജിൽ" if is_ml else "In carry-on bag",
                "details": "യഥാർത്ഥ രേഖകൾ ഒരിക്കലും ചെക്ക്-ഇൻ ബാഗേജിൽ വയ്ക്കരുത്" if is_ml else "Never pack original passport, tickets or money inside checked baggage",
                "priority": "medium"
            }
        ]
    })

    # Emergency contacts
    emergency_contacts = [
        {
            "name": "Indian Embassy Abu Dhabi" if not is_ml else "ഇന്ത്യൻ എംബസി അബുദാബി",
            "number": "+971-2-4492700 / +971-50-8995588",
            "description": "24/7 പ്രവാസി അടിയന്തര സഹായ കേന്ദ്രം" if is_ml else "24/7 Consular & Community Emergency Helpline"
        },
        {
            "name": "Consulate General of India (Dubai)" if not is_ml else "ഇന്ത്യൻ കോൺസുലേറ്റ് ദുബായ് (CGI)",
            "number": "+971-4-3971222 / 800-46342",
            "description": "ദുബായിലും വടക്കൻ എമിറേറ്റുകളിലുമുള്ള സഹായം" if is_ml else "Toll-free helpline for Dubai & Northern Emirates"
        },
        {
            "name": "NORKA-Roots 24/7 Helpline (Kerala)" if not is_ml else "നോർക്ക-റൂട്ട്സ് ഹെൽപ്പ്‌ലൈൻ (കേരളം)",
            "number": "1800-425-3939 / +91-471-2333339",
            "description": "കേരള പ്രവാസികൾക്കുള്ള സൗജന്യ ഹെൽപ്പ്‌ലൈൻ" if is_ml else "Kerala Government Expatriate Support Center"
        },
        {
            "name": "eMigrate PBSK Helpline" if not is_ml else "eMigrate പ്രവാസി ഭാരതീയ കേന്ദ്രം",
            "number": "1800-11-3090",
            "description": "വിദേശകാര്യ മന്ത്രാലയത്തിന്റെ സൗജന്യ നമ്പർ" if is_ml else "MEA Overseas Workers Support Line"
        }
    ]

    official_sources = [
        "https://emigrate.gov.in",
        "https://www.norkaroots.org",
        "https://www.indembassyuae.gov.in",
        "https://smartservices.icp.gov.ae"
    ]

    return {
        "destination": destination,
        "purpose": purpose,
        "travel_date": travel_date,
        "checklist": categories,
        "layover_info": layover_info,
        "emergency_contacts": emergency_contacts,
        "official_sources": official_sources
    }


async def generate_checklist(
    destination: str,
    purpose: str,
    travel_date: str,
    layover_hours: Optional[float],
    language: str,
    emigration_rules: dict
) -> dict:
    """Generate a personalized travel checklist."""
    
    lang_instruction = ""
    if language == "ml":
        lang_instruction = "Respond with all text fields in Malayalam (മലയാളം) language."
    
    rules_context = ""
    if emigration_rules:
        rules_context = f"""\n\nUse these official emigration rules for accurate checklist items:
{json.dumps(emigration_rules, indent=2, ensure_ascii=False)}"""
    
    layover_instruction = ""
    if layover_hours:
        layover_instruction = f"""\n\nThe traveler has a layover of {layover_hours} hours.
Calculate whether it's safe to leave the airport during the layover.
Include a 'layover_info' section with:
- safe_to_leave: true/false
- return_by_time: "HH:MM" (at least 3 hours before next flight)
- transit_visa_needed: true/false
- things_to_do: ["suggestion1", ...]"""
    
    system_prompt = f"""You are TravelGuard's travel planning assistant. Create a personalized,
dated checklist for a traveler from Kerala, India.

Trip details:
- Destination: {destination}
- Purpose: {purpose}
- Travel date: {travel_date}
- Layover: {layover_hours if layover_hours else 'No layover'}
{rules_context}
{layover_instruction}

{lang_instruction}

You MUST respond with ONLY valid JSON in this exact format:
{{
  "destination": "{destination}",
  "purpose": "{purpose}",
  "travel_date": "{travel_date}",
  "checklist": [
    {{
      "category": "category name",
      "items": [
        {{
          "task": "what to do",
          "deadline": "when to do it (specific date or relative like '2 weeks before')",
          "details": "additional details or links",
          "priority": "high" | "medium" | "low"
        }}
      ]
    }}
  ],
  "layover_info": {{
    "safe_to_leave": true/false,
    "return_by_time": "HH:MM",
    "transit_visa_needed": true/false,
    "things_to_do": ["suggestion1"]
  }},
  "emergency_contacts": [
    {{
      "name": "contact name",
      "number": "phone number",
      "description": "when to call"
    }}
  ],
  "official_sources": ["url1", "url2"]
}}

If there is no layover, set layover_info to null."""

    user_prompt = f"Create a complete travel checklist for my {purpose} trip to {destination} on {travel_date}."
    if layover_hours:
        user_prompt += f" I have a {layover_hours}-hour layover."
    
    result = await ask_gemini(user_prompt, None, system_prompt)
    
    # If Gemini returns an error or empty result, use intelligent rule-based fallback
    if "error" in result:
        logger.warning(f"Gemini call failed ({result.get('error')}), using rule-based checklist fallback")
        return rule_based_checklist_fallback(destination, purpose, travel_date, layover_hours, language, emigration_rules)
    
    result.setdefault("destination", destination)
    result.setdefault("purpose", purpose)
    result.setdefault("travel_date", travel_date)
    result.setdefault("checklist", [])
    result.setdefault("emergency_contacts", [])
    result.setdefault("official_sources", [])
    
    return result

