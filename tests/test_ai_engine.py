"""
Tests for the AI engine module.
These tests do NOT require model downloads or a database connection.
"""

import sys
import os

# Make ai_engine importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_engine"))

import pytest
from ai_engine import (
    is_emergency,
    detect_diseases_from_text,
    generate_chat_response,
    EMERGENCY_KEYWORDS,
    MENTAL_HEALTH_KEYWORDS,
    DISEASE_KB,
    DISCLAIMER,
)


class TestEmergencyDetection:
    def test_chest_pain_is_emergency(self):
        assert is_emergency("I have chest pain and can't breathe")

    def test_heart_attack_keyword(self):
        assert is_emergency("I think I'm having a heart attack")

    def test_seizure_keyword(self):
        assert is_emergency("My friend is having a seizure")

    def test_normal_symptoms_not_emergency(self):
        assert not is_emergency("I have a mild cold and runny nose")

    def test_fever_not_emergency(self):
        assert not is_emergency("I have a fever and sore throat")

    def test_case_insensitive(self):
        assert is_emergency("CHEST PAIN and shortness of breath")

    def test_all_keywords_detected(self):
        for kw in EMERGENCY_KEYWORDS:
            assert is_emergency(kw), f"Keyword '{kw}' not detected as emergency"


class TestMentalHealthCrisis:
    def test_suicide_triggers_crisis_response(self):
        result = generate_chat_response("I am thinking about suicide")
        assert result["is_emergency"] is True
        assert "988" in result["response"] or "crisis" in result["response"].lower()

    def test_kill_myself_triggers_crisis_response(self):
        result = generate_chat_response("I want to kill myself")
        assert result["is_emergency"] is True

    def test_crisis_response_contains_helpline(self):
        result = generate_chat_response("I feel suicidal")
        assert result["is_emergency"] is True
        # Should mention a crisis helpline
        assert "988" in result["response"] or "116 123" in result["response"]


class TestDiseaseDetection:
    def test_cold_detected(self):
        diseases = detect_diseases_from_text("I have runny nose and sneezing for 2 days")
        assert "cold" in diseases

    def test_diabetes_by_name(self):
        diseases = detect_diseases_from_text("I was diagnosed with diabetes last year")
        assert "diabetes" in diseases

    def test_fever_by_symptom(self):
        diseases = detect_diseases_from_text("I have high temperature and body aches")
        assert "fever" in diseases

    def test_heart_disease_by_name(self):
        diseases = detect_diseases_from_text("managing heart disease with medication")
        assert "heart disease" in diseases

    def test_no_disease_for_generic_text(self):
        diseases = detect_diseases_from_text("Hello how are you today")
        assert diseases == []

    def test_multiple_diseases(self):
        diseases = detect_diseases_from_text("I have a cough and also diabetes")
        assert "cough" in diseases
        assert "diabetes" in diseases


class TestChatResponse:
    def test_emergency_response_structure(self):
        result = generate_chat_response("I am having a heart attack")
        assert result["is_emergency"] is True
        assert "EMERGENCY" in result["response"]
        assert result["diseases"] == []

    def test_disease_response_contains_disclaimer(self):
        result = generate_chat_response("I have a cold")
        assert not result["is_emergency"]
        assert DISCLAIMER.strip()[:20] in result["response"] or "Disclaimer" in result["response"] or "disclaimer" in result["response"].lower()

    def test_disease_response_contains_diet(self):
        result = generate_chat_response("I have a cold and runny nose")
        assert not result["is_emergency"]
        assert "diet" in result["response"].lower() or "Diet" in result["response"]

    def test_generic_response_for_unknown(self):
        result = generate_chat_response("Hello there")
        assert not result["is_emergency"]
        assert "HealthChat" in result["response"]

    def test_response_keys_present(self):
        result = generate_chat_response("I have a fever")
        assert "response" in result
        assert "is_emergency" in result
        assert "diseases" in result

    def test_diabetes_guidance_has_specialist(self):
        result = generate_chat_response("I have diabetes")
        assert "Endocrinologist" in result["response"] or "Diabetologist" in result["response"]


class TestDiseaseKB:
    def test_all_diseases_have_required_keys(self):
        required_keys = {
            "description", "symptoms", "diet", "home_remedies",
            "lifestyle", "medications_otc", "specialist", "seek_doctor_if",
        }
        for disease, info in DISEASE_KB.items():
            missing = required_keys - info.keys()
            assert not missing, f"Disease '{disease}' missing keys: {missing}"

    def test_five_diseases_present(self):
        assert "cold" in DISEASE_KB
        assert "cough" in DISEASE_KB
        assert "fever" in DISEASE_KB
        assert "diabetes" in DISEASE_KB
        assert "heart disease" in DISEASE_KB
