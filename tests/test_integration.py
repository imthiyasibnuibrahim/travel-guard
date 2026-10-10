"""End-to-end integration tests for TravelGuard API."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "TravelGuard" in response.text
    assert "Safe Journeys Begin Here" in response.text


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_offer_check_scam_english():
    response = client.post(
        "/api/offer-check",
        data={
            "text": "Dubai helper job. Salary AED 15000. Tourist visa provided. Pay Rs 2,50,000 upfront. WhatsApp only +971501234567. Urgent today only!",
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 70
    assert data["risk_level"] == "high"
    assert len(data["red_flags"]) >= 3
    assert len(data["safe_next_steps"]) > 0


def test_offer_check_malayalam():
    response = client.post(
        "/api/offer-check",
        data={
            "text": "Dubai job offer. Pay fee upfront on WhatsApp.",
            "language": "ml"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert any("പണം" in flag or "വിസ" in flag or "വാഗ്ദാനം" in flag or "സമ്മർദ്ദം" in flag for flag in data["red_flags"])


def test_pack_check_items():
    response = client.post(
        "/api/pack-check",
        data={
            "items": "Paracetamol\nCodeine cough syrup\nWhiskey\nHomemade mystery powder",
            "destination": "UAE",
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    items = {item["name"].lower(): item for item in data["items"]}
    
    # Paracetamol should be likely_ok
    assert any("paracetamol" in k and items[k]["status"] == "likely_ok" for k in items)
    # Codeine should be prohibited
    assert any("codeine" in k and items[k]["status"] == "prohibited" for k in items)
    # Whiskey should be restricted
    assert any("whiskey" in k and items[k]["status"] == "restricted" for k in items)
    # Unknown item must be unsure
    assert any("mystery" in k and items[k]["status"] == "unsure" for k in items)


def test_pack_check_malayalam():
    response = client.post(
        "/api/pack-check",
        data={
            "items": "Dolo\nCorex",
            "destination": "UAE",
            "language": "ml"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 2
    assert len(data["general_tips"]) > 0


def test_checklist_work_trip():
    response = client.post(
        "/api/checklist",
        data={
            "destination": "UAE",
            "purpose": "work",
            "travel_date": "2026-11-20",
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["destination"] == "UAE"
    assert data["purpose"] == "work"
    assert len(data["checklist"]) >= 3
    assert len(data["emergency_contacts"]) >= 3


def test_checklist_layover_calculation():
    # Long layover (8 hours) -> Safe to leave
    response = client.post(
        "/api/checklist",
        data={
            "destination": "UAE",
            "purpose": "layover",
            "travel_date": "2026-11-20",
            "layover_hours": 8.0,
            "language": "en"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["layover_info"]["safe_to_leave"] is True
    assert len(data["layover_info"]["return_by_time"]) > 0


    # Short layover (3 hours) -> Unsafe to leave
    response_short = client.post(
        "/api/checklist",
        data={
            "destination": "UAE",
            "purpose": "layover",
            "travel_date": "2026-11-20",
            "layover_hours": 3.0,
            "language": "en"
        }
    )
    assert response_short.status_code == 200
    data_short = response_short.json()
    assert data_short["layover_info"]["safe_to_leave"] is False


def test_checklist_malayalam():
    response = client.post(
        "/api/checklist",
        data={
            "destination": "UAE",
            "purpose": "work",
            "travel_date": "2026-11-20",
            "language": "ml"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["checklist"]) > 0
    # Check that Malayalam text is present
    cat_names = [c["category"] for c in data["checklist"]]
    assert any("രേഖകളും" in name or "ആരോഗ്യവും" in name or "നിർദ്ദേശങ്ങൾ" in name for name in cat_names)
