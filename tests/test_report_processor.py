"""
Tests for the report processor module.
These tests do NOT require external libraries (OCR / PDF parsers) to be installed.
They validate the routing logic and diet advice rules.
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from reports.report_processor import (
    detect_file_type,
    generate_diet_advice_from_text,
    REPORT_DIET_RULES,
)


class TestFileTypeDetection:
    def test_pdf(self):
        assert detect_file_type("report.pdf") == "pdf"

    def test_csv(self):
        assert detect_file_type("bloodwork.csv") == "csv"

    def test_png(self):
        assert detect_file_type("scan.png") == "image"

    def test_jpg(self):
        assert detect_file_type("xray.jpg") == "image"

    def test_jpeg(self):
        assert detect_file_type("photo.JPEG") == "image"

    def test_unknown(self):
        assert detect_file_type("document.docx") == "unknown"

    def test_case_insensitive(self):
        assert detect_file_type("REPORT.PDF") == "pdf"


class TestDietAdvice:
    def test_diabetes_keywords(self):
        text = "Patient has elevated blood glucose and HbA1c is 7.8"
        advice = generate_diet_advice_from_text(text)
        assert "Diabetic" in advice or "glycaemic" in advice.lower()

    def test_cholesterol_keywords(self):
        text = "LDL cholesterol is 180 mg/dL, HDL is low"
        advice = generate_diet_advice_from_text(text)
        assert "Cholesterol" in advice or "omega-3" in advice.lower()

    def test_blood_pressure_keywords(self):
        text = "Systolic blood pressure 145 mmHg, diastolic 90 mmHg, hypertension"
        advice = generate_diet_advice_from_text(text)
        assert "Hypertension" in advice or "sodium" in advice.lower()

    def test_anaemia_keywords(self):
        text = "Haemoglobin 8 g/dL – iron deficiency anaemia"
        advice = generate_diet_advice_from_text(text)
        assert "Anaemia" in advice or "iron" in advice.lower()

    def test_kidney_keywords(self):
        text = "Creatinine 2.1 mg/dL, urea elevated, renal impairment"
        advice = generate_diet_advice_from_text(text)
        assert "Kidney" in advice or "phosphorus" in advice.lower()

    def test_thyroid_keywords(self):
        text = "TSH 8.5 mIU/L, T3 low – hypothyroid pattern"
        advice = generate_diet_advice_from_text(text)
        assert "Thyroid" in advice or "iodine" in advice.lower()

    def test_generic_advice_for_no_keywords(self):
        text = "Patient visited for routine checkup, all results normal"
        advice = generate_diet_advice_from_text(text)
        assert "balanced diet" in advice.lower() or "General" in advice

    def test_all_rules_have_keywords_and_advice(self):
        for keywords, advice in REPORT_DIET_RULES:
            assert len(keywords) > 0
            assert len(advice) > 20
