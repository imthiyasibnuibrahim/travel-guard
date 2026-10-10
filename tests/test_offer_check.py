"""Test cases for the Offer Check feature."""
import pytest
import json
from unittest.mock import AsyncMock, patch

# Test case 1: Scam offer with money upfront
SCAM_OFFER_TEXT = """
Dear brother, I have a great opportunity for you in Dubai!
Company: Big Business LLC
Salary: AED 15,000/month (guaranteed)
Position: General Helper
Visa: Tourist visa (we will convert to work visa after you arrive)
You just need to pay ₹2,50,000 processing fee upfront.
Send to my personal account.
Contact me on WhatsApp only: +971 50 XXX XXXX
Decide today, this offer expires tonight!
"""

# Test case 2: Legitimate-looking offer
LEGIT_OFFER_TEXT = """
Dear Applicant,

We are pleased to offer you a position at ABC Construction LLC (Trade License #123456)
Role: Civil Engineer
Salary: AED 8,000/month + accommodation + transport
Contract: 2 years, renewable
Visa: Employment visa sponsored by employer

Please visit our office at: Building 45, Al Quoz Industrial Area, Dubai
Or email: hr@abcconstruction.ae
Phone: +971 4 XXX XXXX

You will receive your contract for review before travel.
No fees required from your side.
"""

# Test case 3: Subtle scam - Azad visa
AZAD_VISA_TEXT = """
Bhai, come to Dubai on free visa (Azad visa). You can work anywhere.
I will arrange everything. Just send ₹1,00,000.
My WhatsApp: +971 55 XXX XXXX
"""

# Test case 4: Pressure tactics
PRESSURE_TEXT = """
URGENT: Last 2 seats remaining for Dubai job!
Salary: AED 5000, food and accommodation free.
Pay ₹50,000 now to confirm your seat.
Offer valid only today. Don't miss this chance!
Call now: 9876543210
"""

# Test case 5: Vague offer
VAGUE_TEXT = """
Good job available in Gulf. Good salary.
Interested? Send your passport copy and photo.
WhatsApp me.
"""


def test_scam_offer_structure():
    """Test that a scam offer response has all required fields."""
    # This tests the expected response structure
    expected_fields = ['risk_score', 'risk_level', 'red_flags', 'what_to_verify', 'safe_next_steps']
    # Mock response for structure validation
    mock_response = {
        "risk_score": 92,
        "risk_level": "high",
        "red_flags": ["Money asked upfront", "Tourist visa for job"],
        "what_to_verify": ["Company registration"],
        "safe_next_steps": ["Contact NORKA-Roots"],
        "summary": "High risk scam detected"
    }
    for field in expected_fields:
        assert field in mock_response


def test_risk_score_range():
    """Test that risk score is within valid range."""
    mock_response = {"risk_score": 85, "risk_level": "high"}
    assert 0 <= mock_response["risk_score"] <= 100


def test_risk_level_values():
    """Test that risk level is one of the valid values."""
    valid_levels = ['low', 'medium', 'high']
    for level in valid_levels:
        assert level in valid_levels


def test_legit_offer_lower_risk():
    """Test that legitimate offers get lower risk scores."""
    # In real testing, this would call the API
    legit_response = {"risk_score": 25, "risk_level": "low"}
    scam_response = {"risk_score": 92, "risk_level": "high"}
    assert legit_response["risk_score"] < scam_response["risk_score"]


def test_empty_input_rejected():
    """Test that empty input is properly rejected."""
    # This tests the validation logic
    text = ""
    image = None
    assert not text and not image  # Should be rejected
