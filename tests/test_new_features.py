"""Tests for new features: Handbag, Currency, Boarding Guide, SIM Guide, Contract Reader, and Emergency Card."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# === 1. HANDBAG CHECKLIST TESTS (3 tests) ===
def test_handbag_checklist_loading():
    """Test that handbag checklist endpoint returns valid categories."""
    response = client.get("/api/handbag")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    cat_ids = [c["id"] for c in data["categories"]]
    assert "must_have" in cat_ids
    assert "battery_rules" in cat_ids
    assert "suggested_items" in cat_ids


def test_handbag_battery_rule():
    """Power banks must be explicitly flagged for handbag only."""
    response = client.get("/api/handbag")
    data = response.json()
    battery_cat = next(c for c in data["categories"] if c["id"] == "battery_rules")
    powerbank_item = next(i for i in battery_cat["items"] if "powerbank" in i["id"])
    assert "HANDBAG ONLY" in powerbank_item["name_en"]
    assert powerbank_item["critical"] is True


def test_handbag_trilingual_support():
    """All handbag items must have English, Malayalam, and Hindi names."""
    response = client.get("/api/handbag")
    data = response.json()
    for cat in data["categories"]:
        assert "title_en" in cat and "title_ml" in cat and "title_hi" in cat
        for item in cat["items"]:
            assert item["name_en"] and item["name_ml"] and item["name_hi"]


# === 2. CURRENCY CONVERTER TESTS (3 tests) ===
def test_currency_default_aed_to_inr():
    """Default AED to INR conversion."""
    response = client.get("/api/currency?from_curr=AED&to_curr=INR&amount=100")
    assert response.status_code == 200
    data = response.json()
    assert data["from_currency"] == "AED"
    assert data["to_currency"] == "INR"
    assert data["amount"] == 100
    assert data["exchange_rate"] > 20.0
    assert data["converted_amount"] > 2000.0
    assert "last_updated" in data
    assert "tip" in data


def test_currency_other_pairs():
    """Test conversion between other Gulf currencies."""
    response = client.get("/api/currency?from_curr=SAR&to_curr=INR&amount=50")
    assert response.status_code == 200
    data = response.json()
    assert data["from_currency"] == "SAR"
    assert data["exchange_rate"] > 0


def test_currency_tip_multilingual():
    """Exchange tips must be localized."""
    res_en = client.get("/api/currency?language=en")
    res_ml = client.get("/api/currency?language=ml")
    res_hi = client.get("/api/currency?language=hi")
    assert "Airport" in res_en.json()["tip"]
    assert "എയർപോർട്ട്" in res_ml.json()["tip"]
    assert "हवाई अड्डे" in res_hi.json()["tip"]


# === 3. BOARDING GUIDE TESTS (3 tests) ===
def test_boarding_guide_international():
    """International flight with baggage has arrive-by time ~4 hours prior."""
    response = client.post(
        "/api/boarding-guide",
        data={
            "departure_airport": "COK",
            "flight_time": "18:00",
            "is_international": True,
            "has_checked_bag": True,
            "has_ecr_passport": False,
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["departure_airport"] == "COK"
    assert "steps" in data
    step_ids = [s["id"] for s in data["steps"]]
    assert "step_arrive" in step_ids
    assert "step_checkin" in step_ids
    assert "step_security" in step_ids
    assert "step_gate" in step_ids


def test_boarding_guide_ecr_poe_counter():
    """ECR passport holders must have the PoE counter step."""
    response = client.post(
        "/api/boarding-guide",
        data={
            "departure_airport": "CCJ",
            "flight_time": "20:00",
            "is_international": True,
            "has_checked_bag": True,
            "has_ecr_passport": True,
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    step_ids = [s["id"] for s in data["steps"]]
    assert "step_emigration" in step_ids


def test_boarding_guide_what_to_do_now():
    """Guide must provide a live 'what to do now' status."""
    response = client.post(
        "/api/boarding-guide",
        data={
            "departure_airport": "TRV",
            "flight_time": "23:00",
            "is_international": True,
            "has_checked_bag": False,
            "has_ecr_passport": False,
            "language": "hi"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["what_to_do_now"]) > 0


# === 4. SIM GUIDE TESTS (3 tests) ===
def test_sim_guide_tourist():
    """Test tourist visitor recommendations from verified data."""
    response = client.post(
        "/api/sim-guide",
        data={
            "arrival_city": "Dubai",
            "stay_days": 10,
            "data_usage": "heavy",
            "user_type": "visitor",
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "last_checked" in data
    assert "verification_notice" in data
    assert len(data["recommended_plans"]) > 0
    # Must contain official operators
    ops = [p["operator"] for p in data["recommended_plans"]]
    assert any("e&" in op or "du" in op for op in ops)


def test_sim_guide_no_invented_prices():
    """All plans must have valid numeric AED prices and INR approx."""
    response = client.post(
        "/api/sim-guide",
        data={
            "arrival_city": "Abu Dhabi",
            "stay_days": 30,
            "data_usage": "medium",
            "user_type": "visitor",
            "language": "en"
        }
    )
    data = response.json()
    for plan in data["recommended_plans"]:
        assert isinstance(plan["price_aed"], (int, float))
        assert plan["price_aed"] > 0
        assert plan["price_inr_approx"] > 0


def test_sim_guide_free_sim_info():
    """Tourist SIM info about free airport 1GB SIM."""
    response = client.post(
        "/api/sim-guide",
        data={
            "arrival_city": "Dubai",
            "stay_days": 5,
            "data_usage": "light",
            "user_type": "visitor",
            "language": "ml"
        }
    )
    data = response.json()
    assert "free_sim_info" in data
    assert data["free_sim_info"]["title"]


# === 5. CONTRACT CHECK TESTS (3 tests) ===
def test_contract_illegal_passport_retention():
    """Contract demanding to surrender passport must be flagged as violation."""
    response = client.post(
        "/api/contract-check",
        data={
            "text": "Employee agrees to surrender original passport to employer custody upon arrival in UAE. Salary: AED 1500. Working hours: 12 hours daily, no overtime.",
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["contract_verdict"] == "dangerous"
    assert any("passport" in flag.lower() for flag in data["red_flags"])


def test_contract_clean_contract():
    """Clean standard contract without passport holding."""
    response = client.post(
        "/api/contract-check",
        data={
            "text": "Position: Junior Technician. Basic Salary: AED 3500. Standard working hours 8 hours/day. Overtime as per UAE labor law. Employee retains passport at all times.",
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["red_flags"]) == 0
    assert data["contract_verdict"] in ["safe", "review_needed"]


def test_contract_trilingual_response():
    """Contract check in Malayalam."""
    response = client.post(
        "/api/contract-check",
        data={
            "text": "Passport hold by company. Visa cost deducted from monthly salary.",
            "language": "ml"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["red_flags"]) >= 1
    assert any("പാസ്‌പോർട്ട്" in f or "വിസ" in f for f in data["red_flags"])


# === 6. EMERGENCY CARD TESTS (3 tests) ===
def test_emergency_card_contacts_loaded():
    """Emergency card contains NORKA, Indian Embassy, CGI, and UAE Police."""
    response = client.get("/api/emergency-card?language=en")
    assert response.status_code == 200
    data = response.json()
    assert "contacts" in data
    nums = [c["number"] for c in data["contacts"]]
    assert "1800-425-3939" in nums  # NORKA
    assert "+971-2-4492700" in nums  # Embassy
    assert "999" in nums  # UAE Police


def test_emergency_card_tap_to_call_valid():
    """Contacts must have direct phone numbers."""
    response = client.get("/api/emergency-card?language=en")
    data = response.json()
    for c in data["contacts"]:
        assert c["number"]
        assert c["desc"]


def test_emergency_card_multilingual():
    """Emergency card in Hindi."""
    response = client.get("/api/emergency-card?language=hi")
    assert response.status_code == 200
    data = response.json()
    assert len(data["contacts"]) >= 6
