import json
import logging
from typing import Optional
from services.gemini_service import ask_gemini

logger = logging.getLogger(__name__)


def rule_based_pack_fallback(items_text: Optional[str], destination: str, language: str, restricted_items_data: dict) -> dict:
    """Intelligent rule-based fallback strictly grounded in restricted_items.json."""
    is_ml = language == "ml"
    is_hi = language == "hi"
    raw_items = []
    if items_text:
        # Split by newlines and commas
        for line in items_text.replace(",", "\n").split("\n"):
            clean_item = line.strip()
            if clean_item:
                raw_items.append(clean_item)
    
    if not raw_items:
        raw_items = ["Sample item"]

    dest_data = restricted_items_data.get("destinations", {}).get(destination, {})
    prohibited_list = dest_data.get("prohibited_items", [])
    restricted_list = dest_data.get("restricted_items", [])

    analyzed_items = []

    for item_name in raw_items:
        lower_name = item_name.lower()
        matched = False

        # 1. Check prohibited items
        for p in prohibited_list:
            keywords = [k.lower() for k in p.get("keywords", [])]
            if any(k in lower_name for k in keywords) or p.get("item", "").lower() in lower_name:
                analyzed_items.append({
                    "name": item_name,
                    "status": "prohibited",
                    "reason": (
                        f"കർശനമായി നിരോധിച്ചിരിക്കുന്നു: {p.get('reason', '')}" if is_ml
                        else (f"कड़ाई से प्रतिबंधित: {p.get('reason', '')}" if is_hi
                        else p.get("reason", "Strictly prohibited by destination customs."))
                    ),
                    "paperwork_needed": (
                        "യാതൊരു കാരണവശാലും കൊണ്ടുപോകാൻ അനുവാദമില്ല" if is_ml
                        else ("किसी भी परिस्थिति में ले जाने की अनुमति नहीं है" if is_hi
                        else "Cannot be brought under any circumstances")
                    )
                })
                matched = True
                break

        if matched:
            continue

        # 2. Check restricted / permitted items from database
        for r in restricted_list:
            keywords = [k.lower() for k in r.get("keywords", [])]
            if any(k in lower_name for k in keywords) or r.get("item", "").lower() in lower_name:
                status = r.get("status", "restricted")
                analyzed_items.append({
                    "name": item_name,
                    "status": status,
                    "reason": (
                        f"നിയന്ത്രിതം: {r.get('reason', '')}" if is_ml
                        else (f"प्रतिबंधित/शर्तों के साथ: {r.get('reason', '')}" if is_hi
                        else r.get("reason", ""))
                    ),
                    "paperwork_needed": (
                        r.get("paperwork_needed", "ഡോക്ടറുടെ കുറിപ്പടി ആവശ്യമാണ്" if status == "restricted" else "ആവശ്യമില്ല") if is_ml
                        else (r.get("paperwork_needed", "डॉक्टर का पर्चा अनिवार्य है" if status == "restricted" else "कुछ नहीं") if is_hi
                        else r.get("paperwork_needed", "Prescription required" if status == "restricted" else "None"))
                    )
                })
                matched = True
                break

        if matched:
            continue

        # 3. If item is NOT in the database, return "unsure" - Never guess confidently!
        analyzed_items.append({
            "name": item_name,
            "status": "unsure",
            "reason": (
                "ഈ സാധനം ഞങ്ങളുടെ ഔദ്യോഗിക ഡാറ്റാബേസിൽ കണ്ടെത്തിയില്ല. അതിനാൽ യാത്രയ്ക്ക് മുൻപ് യുഎഇ കസ്റ്റംസുമായി നേരിട്ട് ബന്ധപ്പെട്ട് സ്ഥിരീകരിക്കുക." if is_ml
                else ("यह वस्तु आधिकारिक डेटाबेस में नहीं मिली। यात्रा से पहले यूएई कस्टम्स से पुष्टि करें। अनुमान न लगाएं।" if is_hi
                else "Item not found in our curated restricted items database. Please verify with official customs authority before packing. Never assume it is safe.")
            ),
            "paperwork_needed": (
                "കസ്റ്റംസ് അതോറിറ്റിയുമായി പരിശോധിക്കുക (https://www.fca.gov.ae)" if is_ml
                else ("कस्टम्स विभाग से जांचें (https://www.fca.gov.ae)" if is_hi
                else "Verify with UAE Federal Customs Authority (https://www.fca.gov.ae)")
            )
        })

    if is_ml:
        general_tips = [
            "എല്ലാ മരുന്നുകളും യഥാർത്ഥ പാക്കിംഗിലും ലേബലിലും മാത്രം കൊണ്ടുപോകുക",
            "ഡോക്ടറുടെ ഒപ്പും സീലുമുള്ള കുറിപ്പടി (Prescription) നിർബന്ധമായും കൈയിൽ കരുതുക",
            "സംശയമുള്ള സാധനങ്ങൾ വിമാനത്താവളത്തിലെ കസ്റ്റംസിൽ റെഡ് ചാനലിൽ ഡിക്ലയർ ചെയ്യുക"
        ]
    elif is_hi:
        general_tips = [
            "सभी दवाइयां मूल पैकेजिंग और स्पष्ट लेबल के साथ ही ले जाएं",
            "डॉक्टर का हस्ताक्षरित और मुहर लगा पर्चा हमेशा साथ रखें",
            "संदेह होने पर एयरपोर्ट कस्टम्स के रेड चैनल पर सामान की घोषणा करें"
        ]
    else:
        general_tips = [
            "Always carry medicines in their original labeled packaging with maximum 3-month supply",
            "Keep an official doctor's prescription with hospital seal and registration number",
            "Always declare items you are unsure about at customs - penalties for non-declaration are severe"
        ]

    return {
        "destination": destination,
        "items": analyzed_items,
        "general_tips": general_tips,
        "official_source": "UAE Federal Customs Authority (https://www.fca.gov.ae) & UAE MOHAP (https://mohap.gov.ae)"
    }


async def analyze_items(
    items_text: Optional[str],
    image_bytes: Optional[bytes],
    destination: str,
    language: str,
    restricted_items_data: dict
) -> dict:
    """Check if items are allowed in the destination country."""
    
    lang_instruction = ""
    if language == "ml":
        lang_instruction = "Respond with all text fields in Malayalam (മലയാളം) language."
    elif language == "hi":
        lang_instruction = "Respond with all text fields in Hindi (हिन्दी) language."

    
    items_context = ""
    if restricted_items_data:
        items_context = f"""\n\nUse this official restricted items database as ground truth. 
If an item matches something in this database, use the database status and reason.
If an item is NOT in this database, mark it as "unsure" and tell the user to verify with official sources.

Database:
{json.dumps(restricted_items_data, indent=2, ensure_ascii=False)}"""
    
    system_prompt = f"""You are TravelGuard's packing assistant. You help travelers check if their 
items (especially medicines, food, electronics, and personal items) are allowed in their 
destination country.

Destination: {destination}
{items_context}

{lang_instruction}

IMPORTANT RULES:
- If an item clearly matches the restricted items database, use the database info.
- If an item is NOT in the database, mark status as "unsure" - NEVER guess confidently.
- For medicines, always recommend carrying a doctor's prescription.
- Be conservative: when in doubt, mark as "unsure".

You MUST respond with ONLY valid JSON in this exact format:
{{
  "destination": "{destination}",
  "items": [
    {{
      "name": "item name",
      "status": "likely_ok" | "restricted" | "prohibited" | "unsure",
      "reason": "explanation",
      "paperwork_needed": "what documents are needed, or 'None'"
    }}
  ],
  "general_tips": ["tip1", "tip2"],
  "official_source": "URL or name of official customs authority"
}}"""

    user_prompt = ""
    if items_text:
        user_prompt = f"Check if these items are allowed for travel to {destination}:\n\n{items_text}"
    elif image_bytes:
        user_prompt = f"Look at this image and identify the items shown (medicines, products, etc.). Then check if each item is allowed for travel to {destination}."
    
    result = await ask_gemini(user_prompt, image_bytes, system_prompt)
    
    # If Gemini returns an error or empty result, use intelligent rule-based fallback
    if "error" in result:
        logger.warning(f"Gemini call failed ({result.get('error')}), using rule-based pack check fallback")
        return rule_based_pack_fallback(items_text, destination, language, restricted_items_data)
    
    result.setdefault("destination", destination)
    result.setdefault("items", [])
    result.setdefault("general_tips", [])
    result.setdefault("official_source", "UAE Federal Customs Authority")
    
    return result

