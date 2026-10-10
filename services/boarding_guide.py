import logging
from datetime import datetime, timedelta, time
from typing import Optional

logger = logging.getLogger(__name__)


def parse_time_str(time_str: str) -> datetime:
    """Parse time string into datetime object for today."""
    now = datetime.now()
    clean_str = time_str.strip().replace(" ", "").upper()
    
    # Try various formats
    for fmt in ["%H:%M", "%I:%M%p", "%I%p", "%H%M"]:
        try:
            t = datetime.strptime(clean_str, fmt).time()
            return datetime.combine(now.date(), t)
        except ValueError:
            continue
            
    # Fallback default: 4 hours from now
    return now + timedelta(hours=4)


def generate_boarding_timeline(
    departure_airport: str = "COK",
    flight_time_str: str = "15:30",
    is_international: bool = True,
    has_checked_bag: bool = True,
    has_ecr_passport: bool = False,
    language: str = "en"
) -> dict:
    now = datetime.now()
    flight_dt = parse_time_str(flight_time_str)
    
    # If flight time is earlier than current time today, assume next day
    if flight_dt < now - timedelta(hours=2):
        flight_dt += timedelta(days=1)

    # Lead times in minutes
    if is_international:
        arrive_lead = 240 if (has_checked_bag or has_ecr_passport) else 180
        checkin_lead = 210 if has_checked_bag else 150
        emigration_lead = 160
        security_lead = 120
        immigration_lead = 90
        gate_lead = 45
        gate_close_lead = 20
    else:
        arrive_lead = 120
        checkin_lead = 100
        emigration_lead = 0
        security_lead = 60
        immigration_lead = 0
        gate_lead = 35
        gate_close_lead = 15

    # Timestamps
    t_arrive = flight_dt - timedelta(minutes=arrive_lead)
    t_checkin = flight_dt - timedelta(minutes=checkin_lead)
    t_emigration = flight_dt - timedelta(minutes=emigration_lead)
    t_security = flight_dt - timedelta(minutes=security_lead)
    t_immigration = flight_dt - timedelta(minutes=immigration_lead)
    t_gate = flight_dt - timedelta(minutes=gate_lead)
    t_close = flight_dt - timedelta(minutes=gate_close_lead)

    steps = [
        {
            "id": "step_arrive",
            "time": t_arrive.strftime("%H:%M"),
            "minutes_before": arrive_lead,
            "title_en": f"Arrive at {departure_airport} Terminal",
            "title_ml": f"{departure_airport} എയർപോർട്ടിൽ എത്തുക",
            "title_hi": f"{departure_airport} एयरपोर्ट टर्मिनल पर पहुंचें",
            "tip_en": "Keep passport and printed ticket ready at the entry gate for CISF/security inspection.",
            "tip_ml": "പ്രവേശന കവാടത്തിൽ കാണിക്കാൻ പാസ്‌പോർട്ടും ടിക്കറ്റും കൈയിൽ കരുതുക.",
            "tip_hi": "प्रवेश द्वार पर सीआईएसएफ जांच के लिए टिकट और पासपोर्ट तैयार रखें।"
        },
        {
            "id": "step_checkin",
            "time": t_checkin.strftime("%H:%M"),
            "minutes_before": checkin_lead,
            "title_en": "Airline Check-in & Baggage Drop",
            "title_ml": "എയർലൈൻ ചെക്ക്-ഇൻ & ലഗേജ് ഡ്രോപ്പ്",
            "title_hi": "एयरलाइन चेक-इन और बैगेज ड्रॉप",
            "tip_en": "Verify checked bag weight (typically 20-30kg). NO power banks or lighters in checked bags!",
            "tip_ml": "ലഗേജ് തൂക്കം ശ്രദ്ധിക്കുക. പവർബാങ്ക് ചെക്ക്-ഇൻ ബാഗിൽ ഇടരുത്!",
            "tip_hi": "चेक-इन बैग का वजन जांचें। पावर बैंक और लाइटर चेक-इन बैग में बिल्कुल न डालें!"
        }
    ]

    if is_international and has_ecr_passport:
        steps.append({
            "id": "step_emigration",
            "time": t_emigration.strftime("%H:%M"),
            "minutes_before": emigration_lead,
            "title_en": "Protector of Emigrants (PoE) Counter",
            "title_ml": "പ്രൊട്ടക്ടർ ഓഫ് എമിഗ്രന്റ്സ് (PoE) കൗണ്ടർ",
            "title_hi": "प्रोटेक्टर ऑफ इमिग्रेंट्स (PoE) काउंटर",
            "tip_en": "Mandatory for ECR passport holders going on work visa. Present your eMigrate approval number and employment contract.",
            "tip_ml": "തൊഴിൽ വിസയിലുള്ള ECR പാസ്‌പോർട്ടുകാർക്ക് നിർബന്ധമാണ്. eMigrate അപ്രൂവൽ കാണിക്കുക.",
            "tip_hi": "वर्क वीजा पर जाने वाले ईसीआर पासपोर्ट धारकों के लिए अनिवार्य। ईमाइग्रेट अनुमति पत्र दिखाएं।"
        })

    if is_international:
        steps.append({
            "id": "step_immigration",
            "time": t_immigration.strftime("%H:%M"),
            "minutes_before": immigration_lead,
            "title_en": "Passport Control & Immigration",
            "title_ml": "പാസ്‌പോർട്ട് കൺട്രോൾ & ഇമിഗ്രേഷൻ",
            "title_hi": "पासपोर्ट कंट्रोल और इमिग्रेशन जांच",
            "tip_en": "Answer questions calmly. Mention your employer name and destination city clearly. Keep boarding pass stamped.",
            "tip_ml": "ഉത്തരങ്ങൾ കൃത്യമായി നൽകുക. കമ്പനിയുടെ പേരും നഗരവും വ്യക്തമായി പറയുക.",
            "tip_hi": "सवालों के शांत भाव से उत्तर दें। अपनी कंपनी और शहर का नाम स्पष्ट रूप से बताएं।"
        })

    steps.append({
        "id": "step_security",
        "time": t_security.strftime("%H:%M"),
        "minutes_before": security_lead,
        "title_en": "Security Frisking & Handbag X-Ray",
        "title_ml": "സെക്യൂരിറ്റി പരിശോധന",
        "title_hi": "सुरक्षा जांच और हैंडबैग एक्स-रे",
        "tip_en": "Place laptops, tablets, and power banks in separate trays. Discard any water bottles or liquids > 100ml.",
        "tip_ml": "ലാപ്‌ടോപ്പും പവർബാങ്കും പ്രത്യേക ട്രേയിൽ വയ്ക്കുക. 100 മില്ലിക്ക് മുകളിലുള്ള വെള്ളം ഒഴിവാക്കുക.",
        "tip_hi": "लैपटॉप और पावर बैंक को अलग ट्रे में रखें। 100 मिली से अधिक तरल पदार्थ बाहर निकाल दें।"
    })

    steps.append({
        "id": "step_gate",
        "time": t_gate.strftime("%H:%M"),
        "minutes_before": gate_lead,
        "title_en": "At Departure Gate",
        "title_ml": "ബോർഡിംഗ് ഗേറ്റിൽ എത്തുക",
        "title_hi": "बोर्डिंग गेट पर पहुंचें",
        "tip_en": f"Check flight info display screens for any gate change. Gates close strictly at {t_close.strftime('%H:%M')} (20 mins before departure)!",
        "tip_ml": f"ഗേറ്റ് മാറിയിട്ടുണ്ടോ എന്ന് സ്ക്രീനിൽ പരിശോധിക്കുക. {t_close.strftime('%H:%M')} ന് ഗേറ്റ് അടയ്ക്കും!",
        "tip_hi": f"स्क्रीन पर गेट नंबर जांचें। बोर्डिंग गेट प्रस्थान से 20 मिनट पहले ({t_close.strftime('%H:%M')}) बंद हो जाता है।"
    })

    # Determine "What to do right now"
    minutes_until_flight = int((flight_dt - now).total_seconds() / 60)
    
    if minutes_until_flight > arrive_lead:
        current_status = {
            "en": f"You have plenty of time. Double-check your documents and start for {departure_airport} so you arrive by {t_arrive.strftime('%H:%M')}.",
            "ml": f"ധാരാളം സമയമുണ്ട്. രേഖകൾ ഉറപ്പുവരുത്തി {t_arrive.strftime('%H:%M')} ന് വിമാനത്താവളത്തിൽ എത്തുന്ന തരത്തിൽ യാത്ര തുടങ്ങുക.",
            "hi": f"आपके पास पर्याप्त समय है। दस्तावेज़ जांच लें और {t_arrive.strftime('%H:%M')} तक एयरपोर्ट पहुंचने की तैयारी करें।"
        }
        active_step_id = "step_arrive"
    elif minutes_until_flight > checkin_lead:
        current_status = {
            "en": f"You should be at the airport now. Proceed to the airline check-in counters.",
            "ml": f"ഇപ്പോൾ എയർപോർട്ടിൽ എത്തിയിരിക്കണം. എയർലൈൻ ചെക്ക്-ഇൻ കൗണ്ടറിലേക്ക് പോകുക.",
            "hi": f"अब आपको एयरपोर्ट पर होना चाहिए। सीधे अपनी एयरलाइन के चेक-इन काउंटर पर जाएं।"
        }
        active_step_id = "step_checkin"
    elif minutes_until_flight > security_lead:
        current_status = {
            "en": "Check-in completed? Head directly to Immigration and Security screening without delay.",
            "ml": "ചെക്ക്-ഇൻ കഴിഞ്ഞെങ്കിൽ ഉടൻ തന്നെ ഇമിഗ്രേഷൻ, സെക്യൂരിറ്റി പരിശോധനകളിലേക്ക് കടക്കുക.",
            "hi": "चेक-इन के बाद बिना किसी देरी के इमिग्रेशन और सुरक्षा जांच के लिए आगे बढ़ें।"
        }
        active_step_id = "step_immigration" if is_international else "step_security"
    elif minutes_until_flight > gate_lead:
        current_status = {
            "en": f"Security cleared! Walk to your Departure Gate immediately. Gate closes at {t_close.strftime('%H:%M')}.",
            "ml": f"സെക്യൂരിറ്റി കഴിഞ്ഞു! ഉടൻ ബോർഡിംഗ് ഗേറ്റിലേക്ക് പോകുക. {t_close.strftime('%H:%M')} ന് ഗേറ്റ് അടയ്ക്കും.",
            "hi": f"सुरक्षा जांच पूरी हो गई है। तुरंत अपने बोर्डिंग गेट की ओर बढ़ें। गेट {t_close.strftime('%H:%M')} पर बंद हो जाएगा।"
        }
        active_step_id = "step_gate"
    else:
        current_status = {
            "en": f"URGENT: Boarding gate is closing soon! Report to the gate immediately.",
            "ml": "അടിയന്തിരം: ബോർഡിംഗ് പൂർത്തിയാകുന്നു! ഉടൻ ഗേറ്റിൽ റിപ്പോർട്ട് ചെയ്യുക.",
            "hi": "अति आवश्यक: बोर्डिंग गेट बंद होने वाला है! तुरंत गेट पर रिपोर्ट करें।"
        }
        active_step_id = "step_gate"

    return {
        "departure_airport": departure_airport,
        "flight_time": flight_dt.strftime("%H:%M"),
        "minutes_until_flight": minutes_until_flight,
        "arrive_by": t_arrive.strftime("%H:%M"),
        "gate_closes": t_close.strftime("%H:%M"),
        "active_step_id": active_step_id,
        "what_to_do_now": current_status.get(language, current_status["en"]),
        "steps": steps
    }
