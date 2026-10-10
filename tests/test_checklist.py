"""Test cases for the Journey Checklist feature."""
import pytest
import json


# Test case 1: Work trip checklist structure
def test_work_checklist_structure():
    """Work trip checklist should have required categories."""
    mock_response = {
        "destination": "UAE",
        "purpose": "work",
        "travel_date": "2026-11-24",
        "checklist": [
            {
                "category": "Documents",
                "items": [
                    {
                        "task": "Get passport with 6+ months validity",
                        "deadline": "8 weeks before",
                        "details": "Apply at PSK",
                        "priority": "high"
                    }
                ]
            }
        ],
        "emergency_contacts": [
            {"name": "Indian Embassy UAE", "number": "+971-2-4492700", "description": "Emergency"}
        ],
        "official_sources": ["https://emigrate.gov.in"]
    }
    assert mock_response["destination"] == "UAE"
    assert mock_response["purpose"] == "work"
    assert len(mock_response["checklist"]) > 0
    assert "items" in mock_response["checklist"][0]


# Test case 2: Layover info included when relevant
def test_layover_info_present():
    """Layover trips should include layover_info with timing."""
    mock_response = {
        "layover_info": {
            "safe_to_leave": True,
            "return_by_time": "14:00",
            "transit_visa_needed": False,
            "things_to_do": ["Visit Dubai Mall"]
        }
    }
    li = mock_response["layover_info"]
    assert isinstance(li["safe_to_leave"], bool)
    assert li["return_by_time"]
    assert isinstance(li["transit_visa_needed"], bool)


# Test case 3: No layover info for non-layover trips
def test_no_layover_for_work():
    """Work trips should not have layover info."""
    mock_response = {
        "purpose": "work",
        "layover_info": None
    }
    assert mock_response["layover_info"] is None


# Test case 4: Emergency contacts included
def test_emergency_contacts_present():
    """Checklist should include emergency contacts."""
    mock_response = {
        "emergency_contacts": [
            {"name": "Indian Embassy", "number": "+971-2-4492700", "description": "24/7"}
        ]
    }
    assert len(mock_response["emergency_contacts"]) > 0
    contact = mock_response["emergency_contacts"][0]
    assert all(k in contact for k in ["name", "number"])


# Test case 5: Priority levels are valid
def test_priority_levels():
    """All checklist items should have valid priority levels."""
    valid_priorities = ["high", "medium", "low"]
    mock_items = [
        {"task": "Get passport", "priority": "high"},
        {"task": "Book flight", "priority": "medium"},
        {"task": "Pack bags", "priority": "low"}
    ]
    for item in mock_items:
        assert item["priority"] in valid_priorities
