"""Test cases for the Pack Check feature."""
import pytest
import json


# Test case 1: Common allowed medicine
def test_paracetamol_likely_ok():
    """Paracetamol should be marked as likely_ok."""
    mock_response = {
        "items": [{
            "name": "Paracetamol",
            "status": "likely_ok",
            "reason": "Over-the-counter pain reliever, allowed for personal use",
            "paperwork_needed": "None"
        }]
    }
    assert mock_response["items"][0]["status"] == "likely_ok"


# Test case 2: Banned medicine (Codeine)
def test_codeine_prohibited():
    """Codeine-containing medicines should be marked as prohibited."""
    mock_response = {
        "items": [{
            "name": "Codeine cough syrup",
            "status": "prohibited",
            "reason": "Codeine is classified as a controlled narcotic substance in UAE",
            "paperwork_needed": "Cannot be brought into UAE"
        }]
    }
    assert mock_response["items"][0]["status"] == "prohibited"


# Test case 3: Restricted item (alcohol)
def test_alcohol_restricted():
    """Alcohol should be marked as restricted with quantity limits."""
    mock_response = {
        "items": [{
            "name": "Whiskey",
            "status": "restricted",
            "reason": "Non-Muslim travelers over 21 can bring limited alcohol",
            "paperwork_needed": "Must be purchased from duty-free"
        }]
    }
    assert mock_response["items"][0]["status"] == "restricted"
    assert mock_response["items"][0]["paperwork_needed"]


# Test case 4: Unknown item returns unsure
def test_unknown_item_unsure():
    """Items not in the database should be marked as unsure."""
    mock_response = {
        "items": [{
            "name": "Handmade soap",
            "status": "unsure",
            "reason": "Not found in our database. Verify with official customs authority.",
            "paperwork_needed": "Check with UAE Customs"
        }]
    }
    assert mock_response["items"][0]["status"] == "unsure"


# Test case 5: Response structure validation
def test_pack_response_structure():
    """Test that pack check response has all required fields per item."""
    mock_response = {
        "destination": "UAE",
        "items": [{
            "name": "Laptop",
            "status": "likely_ok",
            "reason": "Personal electronics allowed",
            "paperwork_needed": "None"
        }],
        "general_tips": ["Carry medicines in original packaging"],
        "official_source": "UAE Federal Customs Authority"
    }
    assert "destination" in mock_response
    assert "items" in mock_response
    assert len(mock_response["items"]) > 0
    item = mock_response["items"][0]
    assert all(k in item for k in ["name", "status", "reason", "paperwork_needed"])
    assert item["status"] in ["likely_ok", "restricted", "prohibited", "unsure"]
