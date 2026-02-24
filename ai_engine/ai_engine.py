"""
ai_engine.py – Core AI module for HealthChat

Models used (CPU-only, free HuggingFace):
  • dmis-lab/biobert-base-cased-v1.1  → medical text feature extraction / NLP
  • t5-small                           → report summarisation

All model inference runs on CPU only.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy model loading helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_biobert():
    """Load BioBERT tokeniser + model (cached after first call)."""
    from transformers import AutoTokenizer, AutoModel
    import torch

    model_name = "dmis-lab/biobert-base-cased-v1.1"
    logger.info("Loading BioBERT model: %s", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    return tokenizer, model


@lru_cache(maxsize=1)
def _load_t5():
    """Load T5-small tokeniser + model for summarisation (cached)."""
    from transformers import T5Tokenizer, T5ForConditionalGeneration

    model_name = "t5-small"
    logger.info("Loading T5-small model: %s", model_name)
    tokenizer = T5Tokenizer.from_pretrained(model_name)
    model = T5ForConditionalGeneration.from_pretrained(model_name)
    model.eval()
    return tokenizer, model


# ---------------------------------------------------------------------------
# Emergency detection
# ---------------------------------------------------------------------------

EMERGENCY_KEYWORDS: list[str] = [
    "chest pain",
    "heart attack",
    "stroke",
    "difficulty breathing",
    "shortness of breath",
    "can't breathe",
    "cannot breathe",
    "unconscious",
    "unresponsive",
    "severe bleeding",
    "heavy bleeding",
    "not breathing",
    "overdose",
    "collapsed",
    "collapse",
    "seizure",
    "anaphylaxis",
    "allergic reaction",
    "paralysis",
    "sudden numbness",
    "vision loss",
    "sudden blindness",
    "severe headache",
    "worst headache",
]

EMERGENCY_RESPONSE = (
    "🚨 **EMERGENCY DETECTED** 🚨\n\n"
    "Your message contains symptoms that may indicate a **medical emergency**. "
    "Please take the following steps **immediately**:\n\n"
    "1. **Call emergency services** (e.g., 911 / 112 / 999) right now.\n"
    "2. Do NOT wait or try home remedies for emergency symptoms.\n"
    "3. If possible, have someone stay with you until help arrives.\n\n"
    "**Do not rely on this chatbot in an emergency. Seek immediate professional medical help.**\n\n"
    "---\n"
    "*HealthChat is an informational tool and is NOT a substitute for emergency medical care.*"
)

MENTAL_HEALTH_CRISIS_RESPONSE = (
    "🆘 **If you or someone you know is in crisis, please reach out immediately:**\n\n"
    "  • **US**: National Suicide & Crisis Lifeline – call or text **988**\n"
    "  • **UK**: Samaritans – call **116 123** (free, 24/7)\n"
    "  • **International**: [findahelpline.com](https://findahelpline.com)\n\n"
    "You are not alone. Trained counsellors are available right now.\n\n"
    "---\n"
    "*HealthChat is not a mental health crisis service. "
    "Please contact the helplines above for immediate support.*"
)

MENTAL_HEALTH_KEYWORDS: list[str] = ["suicide", "suicidal", "kill myself", "end my life", "self-harm"]


def is_emergency(text: str) -> bool:
    """Return True if the text contains any emergency keyword."""
    lower = text.lower()
    for kw in EMERGENCY_KEYWORDS:
        if kw in lower:
            return True
    return False


# ---------------------------------------------------------------------------
# Disease knowledge base (rule-based)
# ---------------------------------------------------------------------------

DISEASE_KB: dict[str, dict] = {
    "cold": {
        "description": "The common cold is a viral infection of the upper respiratory tract.",
        "symptoms": ["runny nose", "sneezing", "sore throat", "mild fever", "congestion", "cough"],
        "diet": [
            "Drink plenty of warm fluids (water, herbal teas, soups).",
            "Eat vitamin-C rich foods: oranges, lemon, guava.",
            "Avoid cold/icy foods and drinks.",
            "Consume warm broths and light meals.",
        ],
        "home_remedies": [
            "Honey and lemon in warm water.",
            "Ginger tea with tulsi (holy basil).",
            "Steam inhalation with eucalyptus oil.",
            "Saline nasal rinse to relieve congestion.",
        ],
        "lifestyle": [
            "Get adequate rest (7–9 hours of sleep).",
            "Avoid exposure to cold and damp environments.",
            "Wash hands frequently to prevent spread.",
        ],
        "medications_otc": [
            "Paracetamol / Acetaminophen for fever and discomfort.",
            "Antihistamines (e.g., cetirizine) for runny nose.",
            "Decongestants for nasal congestion (consult pharmacist).",
        ],
        "specialist": "General Physician",
        "seek_doctor_if": [
            "Fever above 39 °C (102 °F) lasting more than 3 days.",
            "Severe difficulty breathing.",
            "Symptoms worsen after 7–10 days.",
        ],
    },
    "cough": {
        "description": "A cough is a reflex action that clears the airways of mucus and irritants.",
        "symptoms": ["persistent cough", "dry cough", "wet cough", "throat irritation", "mild fever"],
        "diet": [
            "Warm liquids: herbal teas, honey-lemon water, soups.",
            "Avoid cold drinks and ice cream.",
            "Eat light, easily digestible foods.",
        ],
        "home_remedies": [
            "Honey (1 tsp) before bedtime to soothe throat.",
            "Ginger juice with honey.",
            "Steam inhalation twice daily.",
            "Gargle with warm salt water.",
        ],
        "lifestyle": [
            "Avoid smoking and secondhand smoke.",
            "Humidify indoor air.",
            "Elevate head while sleeping.",
        ],
        "medications_otc": [
            "Dextromethorphan-based cough suppressants for dry cough.",
            "Guaifenesin-based expectorants for productive cough.",
            "Lozenges to soothe throat irritation.",
        ],
        "specialist": "General Physician / Pulmonologist",
        "seek_doctor_if": [
            "Cough lasts more than 3 weeks.",
            "Coughing up blood.",
            "Accompanied by high fever or weight loss.",
        ],
    },
    "fever": {
        "description": "Fever is a temporary increase in body temperature, often due to an infection.",
        "symptoms": ["high temperature", "sweating", "shivering", "headache", "body aches", "weakness"],
        "diet": [
            "Stay well-hydrated: water, ORS, coconut water.",
            "Light foods: khichdi, porridge, bananas, toast.",
            "Avoid oily, spicy, or heavy meals.",
        ],
        "home_remedies": [
            "Lukewarm sponging to bring down temperature.",
            "Cool compress on forehead.",
            "Tulsi (holy basil) and ginger decoction.",
        ],
        "lifestyle": [
            "Rest as much as possible.",
            "Wear light, breathable clothing.",
            "Monitor temperature regularly.",
        ],
        "medications_otc": [
            "Paracetamol (500 mg every 6 hours as needed).",
            "Ibuprofen for adults (avoid in children without medical advice).",
        ],
        "specialist": "General Physician",
        "seek_doctor_if": [
            "Temperature above 39.5 °C (103 °F) in adults.",
            "Fever lasting more than 3 days.",
            "Accompanied by rash, stiff neck, or difficulty breathing.",
        ],
    },
    "diabetes": {
        "description": (
            "Diabetes mellitus is a chronic condition where the body cannot properly "
            "regulate blood glucose levels."
        ),
        "symptoms": [
            "frequent urination",
            "excessive thirst",
            "unexplained weight loss",
            "fatigue",
            "blurred vision",
            "slow-healing wounds",
        ],
        "diet": [
            "Low glycaemic index foods: whole grains, legumes, vegetables.",
            "Avoid sugary beverages, white bread, processed foods.",
            "Small, frequent meals to maintain stable blood sugar.",
            "Include fibre-rich foods: oats, flaxseeds, leafy greens.",
            "Limit saturated fats; choose lean proteins.",
        ],
        "home_remedies": [
            "Bitter gourd (karela) juice on an empty stomach.",
            "Fenugreek seeds soaked overnight in water.",
            "Cinnamon tea (consult doctor for amounts).",
        ],
        "lifestyle": [
            "Regular aerobic exercise: 150 min/week (brisk walking, cycling).",
            "Monitor blood sugar levels regularly.",
            "Maintain healthy body weight.",
            "Avoid smoking and excessive alcohol.",
            "Manage stress through yoga or meditation.",
        ],
        "medications_otc": [
            "Note: Diabetes medications require a doctor's prescription.",
            "OTC blood glucose monitoring strips and devices.",
        ],
        "specialist": "Endocrinologist / Diabetologist",
        "seek_doctor_if": [
            "Blood sugar consistently above normal range.",
            "Symptoms of hypoglycaemia (dizziness, sweating, confusion).",
            "Wounds that do not heal.",
            "Vision changes.",
        ],
    },
    "heart disease": {
        "description": (
            "Heart disease encompasses conditions affecting the heart's structure and function, "
            "including coronary artery disease and heart failure."
        ),
        "symptoms": [
            "chest pain or tightness",
            "shortness of breath",
            "palpitations",
            "fatigue",
            "dizziness",
            "swollen legs",
        ],
        "diet": [
            "Heart-healthy diet: fruits, vegetables, whole grains, legumes.",
            "Limit sodium intake to reduce blood pressure.",
            "Avoid trans fats and saturated fats.",
            "Include omega-3 fatty acids: fish, flaxseeds, walnuts.",
            "Limit alcohol consumption.",
        ],
        "home_remedies": [
            "Garlic (one clove daily) may support heart health.",
            "Green tea for antioxidants.",
            "Stress-reduction: yoga, meditation, deep breathing.",
        ],
        "lifestyle": [
            "Regular moderate exercise (as advised by doctor).",
            "Quit smoking immediately.",
            "Control blood pressure and cholesterol.",
            "Maintain healthy weight.",
            "Regular medical check-ups.",
        ],
        "medications_otc": [
            "Note: Heart disease medications require a doctor's prescription.",
            "Aspirin 75–100 mg (only if previously prescribed by a doctor).",
        ],
        "specialist": "Cardiologist",
        "seek_doctor_if": [
            "Any chest pain, pressure, or tightness.",
            "Shortness of breath at rest.",
            "Sudden dizziness or fainting.",
            "Irregular heartbeat.",
        ],
    },
}

# Symptom → disease mapping for quick detection
SYMPTOM_DISEASE_MAP: dict[str, list[str]] = {}
for _disease, _info in DISEASE_KB.items():
    for _symptom in _info["symptoms"]:
        SYMPTOM_DISEASE_MAP.setdefault(_symptom, []).append(_disease)


# ---------------------------------------------------------------------------
# NLP helpers using BioBERT
# ---------------------------------------------------------------------------

def encode_text(text: str) -> "torch.Tensor":
    """
    Encode medical text using BioBERT and return the [CLS] embedding.
    Used for semantic similarity / future RAG retrieval.
    """
    import torch

    tokenizer, model = _load_biobert()
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True,
    )
    with torch.no_grad():
        outputs = model(**inputs)
    # [CLS] token representation
    cls_embedding = outputs.last_hidden_state[:, 0, :]
    return cls_embedding


def detect_diseases_from_text(text: str) -> list[str]:
    """
    Detect possible diseases mentioned or implied in the user message
    using keyword matching against the symptom/disease knowledge base.
    """
    lower = text.lower()
    detected: set[str] = set()

    # Direct disease name match
    for disease in DISEASE_KB:
        if disease in lower:
            detected.add(disease)

    # Symptom-based match
    for symptom, diseases in SYMPTOM_DISEASE_MAP.items():
        if symptom in lower:
            detected.update(diseases)

    return list(detected)


# ---------------------------------------------------------------------------
# Response generation
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "\n\n---\n"
    "⚠️ **Medical Disclaimer**: This information is for general educational purposes only "
    "and is NOT a substitute for professional medical advice, diagnosis, or treatment. "
    "Always consult a qualified healthcare professional before making any medical decisions."
)


def build_disease_response(diseases: list[str]) -> str:
    """Build a structured guidance response for detected diseases."""
    if not diseases:
        return ""

    parts: list[str] = []
    for disease in diseases:
        info = DISEASE_KB.get(disease)
        if not info:
            continue
        section = [
            f"## {disease.title()}",
            f"**About**: {info['description']}",
            "",
            "**🥗 Diet Recommendations:**",
            *[f"  • {d}" for d in info["diet"]],
            "",
            "**🏠 Home Remedies:**",
            *[f"  • {r}" for r in info["home_remedies"]],
            "",
            "**🏃 Lifestyle Changes:**",
            *[f"  • {l}" for l in info["lifestyle"]],
            "",
            "**💊 OTC Medication Suggestions:**",
            *[f"  • {m}" for m in info["medications_otc"]],
            "",
            f"**👨‍⚕️ Recommended Specialist**: {info['specialist']}",
            "",
            "**🏥 See a Doctor If:**",
            *[f"  • {s}" for s in info["seek_doctor_if"]],
        ]
        parts.append("\n".join(section))

    return "\n\n---\n\n".join(parts)


def _is_mental_health_crisis(text: str) -> bool:
    """Return True if the text contains mental health crisis keywords."""
    lower = text.lower()
    return any(kw in lower for kw in MENTAL_HEALTH_KEYWORDS)


def generate_chat_response(user_message: str) -> dict:
    """
    Main chat response function.
    Returns a dict with keys: response (str), is_emergency (bool), diseases (list).
    """
    # 1. Mental health crisis check (highest priority alongside medical emergency)
    if _is_mental_health_crisis(user_message):
        return {
            "response": MENTAL_HEALTH_CRISIS_RESPONSE,
            "is_emergency": True,
            "diseases": [],
        }

    # 2. Medical emergency check
    if is_emergency(user_message):
        return {
            "response": EMERGENCY_RESPONSE,
            "is_emergency": True,
            "diseases": [],
        }

    # 2. Detect diseases / symptoms
    diseases = detect_diseases_from_text(user_message)

    if diseases:
        body = build_disease_response(diseases)
        response = (
            f"Based on your message, I found information related to: "
            f"**{', '.join(d.title() for d in diseases)}**.\n\n"
            + body
            + DISCLAIMER
        )
    else:
        # Generic health guidance
        response = (
            "I'm HealthChat, your AI-powered health assistant. 🩺\n\n"
            "I can help you with information about:\n"
            "  • **Common cold & cough**\n"
            "  • **Fever**\n"
            "  • **Diabetes**\n"
            "  • **Heart disease**\n\n"
            "Please describe your symptoms or mention a health condition and I'll provide "
            "guidance on diet, home remedies, lifestyle changes, and when to see a doctor."
            + DISCLAIMER
        )

    return {
        "response": response,
        "is_emergency": False,
        "diseases": diseases,
    }


# ---------------------------------------------------------------------------
# T5-based summarisation
# ---------------------------------------------------------------------------

def summarise_text(text: str, max_length: int = 200, min_length: int = 40) -> str:
    """
    Summarise medical report text using T5-small.
    Input text is prefixed with 'summarize: ' as required by T5.
    """
    import torch

    tokenizer, model = _load_t5()

    # Pre-tokenisation character limit to avoid extreme overhead on very long texts.
    # The tokenizer will further truncate to 512 tokens below.
    max_input_chars_before_tokenization = 3000
    if len(text) > max_input_chars_before_tokenization:
        text = text[:max_input_chars_before_tokenization]

    input_text = "summarize: " + text
    inputs = tokenizer(
        input_text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )

    with torch.no_grad():
        summary_ids = model.generate(
            inputs["input_ids"],
            max_length=max_length,
            min_length=min_length,
            length_penalty=2.0,
            num_beams=4,
            early_stopping=True,
        )

    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary
