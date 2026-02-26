"""
report_processor.py – Handles extraction of text from PDF, CSV, and image files.
"""

from __future__ import annotations

import io
import logging
import os

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using pdfplumber."""
    try:
        import pdfplumber

        text_parts: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as exc:
        logger.error("PDF extraction error: %s", exc)
        return ""


def extract_text_from_image(file_path: str) -> str:
    """Extract text from an image file using Tesseract OCR via pytesseract."""
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(file_path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as exc:
        logger.error("Image OCR error: %s", exc)
        return ""


def extract_text_from_csv(file_path: str) -> str:
    """Convert a CSV file to a human-readable text summary using Pandas."""
    try:
        import pandas as pd

        df = pd.read_csv(file_path)
        lines: list[str] = []
        lines.append(f"Columns: {', '.join(df.columns.tolist())}")
        lines.append(f"Total rows: {len(df)}")
        lines.append("")
        # Descriptive statistics for numeric columns
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            lines.append("Numeric summary:")
            lines.append(df[numeric_cols].describe().to_string())
            lines.append("")
        # First few rows as context
        lines.append("Sample data (first 5 rows):")
        lines.append(df.head().to_string(index=False))
        return "\n".join(lines)
    except Exception as exc:
        logger.error("CSV extraction error: %s", exc)
        return ""


def detect_file_type(filename: str) -> str:
    """Determine file type from extension."""
    ext = os.path.splitext(filename)[-1].lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".csv":
        return "csv"
    if ext in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp"}:
        return "image"
    return "unknown"


def extract_text(file_path: str, file_type: str) -> str:
    """Route extraction to the correct handler based on file type."""
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    if file_type == "csv":
        return extract_text_from_csv(file_path)
    if file_type == "image":
        return extract_text_from_image(file_path)
    return ""


# ---------------------------------------------------------------------------
# Diet advice from report keywords (rule-based)
# ---------------------------------------------------------------------------

REPORT_DIET_RULES: list[tuple[list[str], str]] = [
    (
        ["diabetes", "blood glucose", "blood sugar", "hba1c", "insulin"],
        (
            "**Diabetic Diet Advice**: Prefer low glycaemic index foods (whole grains, legumes). "
            "Avoid refined sugars and white carbohydrates. Eat small, frequent meals. "
            "Include fibre-rich vegetables and lean proteins."
        ),
    ),
    (
        ["cholesterol", "ldl", "hdl", "triglyceride", "lipid"],
        (
            "**Cholesterol Management Diet**: Reduce saturated and trans fats. "
            "Increase omega-3 intake (fish, flaxseeds, walnuts). "
            "Eat oat-based foods and fibre-rich produce. Limit red meat and full-fat dairy."
        ),
    ),
    (
        ["blood pressure", "hypertension", "systolic", "diastolic"],
        (
            "**Hypertension Diet (DASH)**: Reduce sodium to < 2,300 mg/day. "
            "Eat potassium-rich foods (bananas, sweet potatoes). "
            "Limit alcohol and caffeine. Choose whole grains and low-fat dairy."
        ),
    ),
    (
        ["anaemia", "haemoglobin", "hemoglobin", "iron deficiency"],
        (
            "**Anaemia Diet**: Increase iron-rich foods (spinach, lentils, red meat). "
            "Pair with vitamin C for better absorption. "
            "Avoid tea/coffee with meals as they inhibit iron absorption."
        ),
    ),
    (
        ["kidney", "creatinine", "urea", "renal"],
        (
            "**Kidney-Friendly Diet**: Limit potassium, phosphorus, and sodium. "
            "Control protein intake as advised by your doctor. "
            "Stay hydrated but monitor fluid restriction if prescribed."
        ),
    ),
    (
        ["thyroid", "tsh", "t3", "t4", "hypothyroid", "hyperthyroid"],
        (
            "**Thyroid Diet**: Eat iodine-rich foods (seafood, iodised salt) for hypothyroidism. "
            "Limit goitrogenic foods (raw cabbage, soy) in excess. "
            "Ensure adequate selenium intake (Brazil nuts, tuna)."
        ),
    ),
]


def generate_diet_advice_from_text(text: str) -> str:
    """Generate diet advice based on keywords found in extracted report text."""
    lower = text.lower()
    advice_parts: list[str] = []
    for keywords, advice in REPORT_DIET_RULES:
        if any(kw in lower for kw in keywords):
            advice_parts.append(advice)

    if advice_parts:
        return "\n\n".join(advice_parts)
    return (
        "**General Healthy Diet Advice**: Eat a balanced diet rich in fruits, vegetables, "
        "whole grains, and lean proteins. Stay well hydrated. Limit processed foods, "
        "excess sugar, and saturated fats. Consult a registered dietitian for personalised advice."
    )
