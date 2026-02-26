# 🩺 HealthChat – Smart AI Healthcare Chatbot

A CPU-only, **academic-grade** Smart AI Healthcare Chatbot built with **Django** (backend),
**Streamlit** (frontend), **MySQL** (database), and free HuggingFace transformer models
(**BioBERT** + **T5-small**).

---

## ✨ Features

| Feature | Details |
|---|---|
| 👤 User Auth | Registration, JWT login, profile (age, gender) |
| 💬 Symptom Chat | Natural-language health Q&A with disease guidance |
| 🚨 Emergency Detection | Keyword-based escalation with instant 999/911 alert |
| 🏥 Disease Guidance | Cold, Cough, Fever, Diabetes, Heart Disease |
| 🥗 Recommendations | Diet, home remedies, lifestyle changes, OTC medications, specialist referrals |
| 📄 Report Upload | PDF (pdfplumber), CSV (Pandas), Images (Tesseract OCR) |
| 🤖 AI Summarisation | T5-small summarises medical report text |
| 📚 Conversation History | Full chat history stored in MySQL, browsable in UI |
| ⚠️ Medical Disclaimer | Appended to every AI response |
| 🔒 Safe by design | No diagnosis claims, always recommends doctor consultation |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Frontend                     │
│   (frontend/app.py  •  localhost:8501)                   │
└───────────────────────┬─────────────────────────────────┘
                        │  REST API (JWT)
┌───────────────────────▼─────────────────────────────────┐
│              Django REST Framework Backend               │
│   accounts/   chatbot/   reports/   (localhost:8000)     │
└───────┬───────────────────────────┬─────────────────────┘
        │                           │
┌───────▼──────┐           ┌────────▼───────────┐
│   MySQL DB   │           │   AI Engine Layer   │
│ (healthchat) │           │  ai_engine.py       │
└──────────────┘           │  • BioBERT (NLP)    │
                           │  • T5-small (summ.) │
                           │  • Rule-based KB    │
                           └────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Django 4.2, Django REST Framework, SimpleJWT |
| Frontend | Streamlit |
| Database | MySQL 8+ |
| NLP / AI | `dmis-lab/biobert-base-cased-v1.1`, `t5-small` (HuggingFace) |
| OCR | Tesseract + pytesseract |
| PDF | pdfplumber |
| CSV | Pandas |
| Auth | JWT (access + refresh tokens) |

All AI models run on **CPU only** — no GPU required.

---

## 📁 Project Structure

```
HealthChat/
├── manage.py
├── requirements.txt
├── .env.example           ← copy to .env and configure
├── setup_db.sql           ← MySQL database creation script
├── run_backend.sh         ← start Django server
├── run_frontend.sh        ← start Streamlit UI
│
├── healthchat_backend/    ← Django project settings & URLs
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── accounts/              ← User registration & login
│   ├── models.py          ← UserProfile
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── chatbot/               ← Symptom chat, conversation history
│   ├── models.py          ← Conversation, Message
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── reports/               ← Medical report upload & analysis
│   ├── models.py          ← MedicalReport
│   ├── report_processor.py← PDF / CSV / Image extraction + diet rules
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── ai_engine/
│   └── ai_engine.py       ← BioBERT, T5, emergency detection, disease KB
│
├── frontend/
│   └── app.py             ← Streamlit UI
│
├── media/reports/         ← Uploaded medical reports (auto-created)
│
└── tests/
    ├── test_ai_engine.py
    └── test_report_processor.py
```

---

## 🗄️ Database Schema

### `accounts_userprofile`
| Column | Type | Notes |
|---|---|---|
| id | INT PK | |
| user_id | FK → auth_user | |
| age | SMALLINT NULL | |
| gender | VARCHAR(10) | male / female / other |
| created_at | DATETIME | |

### `chatbot_conversation`
| Column | Type |
|---|---|
| id | INT PK |
| user_id | FK → auth_user |
| title | VARCHAR(255) |
| created_at / updated_at | DATETIME |

### `chatbot_message`
| Column | Type | Notes |
|---|---|---|
| id | INT PK | |
| conversation_id | FK | |
| role | VARCHAR(10) | user / bot |
| content | TEXT | |
| is_emergency | BOOL | |
| diseases_detected | JSON | list of strings |
| timestamp | DATETIME | |

### `reports_medicalreport`
| Column | Type |
|---|---|
| id | INT PK |
| user_id | FK → auth_user |
| file | VARCHAR(255) |
| file_type | VARCHAR(10) |
| original_filename | VARCHAR(255) |
| extracted_text | TEXT |
| summary | TEXT |
| diet_advice | TEXT |
| uploaded_at | DATETIME |
| processed | BOOL |

---

## 🚀 Local Setup (Step by Step)

### Prerequisites
- Python 3.12
- MySQL 8.0+
- Tesseract OCR installed ([install guide](https://tesseract-ocr.github.io/tessdoc/Installation.html))

### 1. Clone and install dependencies

```bash
git clone https://github.com/mdhanush96/HealthChat.git
cd HealthChat
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your MySQL credentials and a strong SECRET_KEY
```

### 3. Create MySQL database

```bash
mysql -u root -p < setup_db.sql
```

### 4. Run Django migrations

```bash
python manage.py migrate
python manage.py createsuperuser  # optional – for admin panel
```

### 5. Start the backend

```bash
bash run_backend.sh
# Django API will be available at http://127.0.0.1:8000
```

### 6. Start the Streamlit frontend (new terminal)

```bash
source venv/bin/activate
bash run_frontend.sh
# UI available at http://localhost:8501
```

### 7. Run tests

```bash
python -m pytest tests/ -v
```

---

## 🔌 API Endpoints

| Method | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register/` | ❌ | Create account |
| POST | `/api/auth/login/` | ❌ | Get JWT tokens |
| POST | `/api/auth/token/refresh/` | ❌ | Refresh access token |
| GET | `/api/auth/me/` | ✅ | Current user profile |
| POST | `/api/chat/message/` | ✅ | Send message, get AI response |
| GET | `/api/chat/conversations/` | ✅ | List all conversations |
| GET | `/api/chat/conversations/<id>/` | ✅ | Conversation detail |
| DELETE | `/api/chat/conversations/<id>/` | ✅ | Delete conversation |
| GET | `/api/chat/history/<conv_id>/` | ✅ | Full message history |
| POST | `/api/reports/upload/` | ✅ | Upload & analyse medical report |
| GET | `/api/reports/` | ✅ | List uploaded reports |
| GET | `/api/reports/<id>/` | ✅ | Report detail |
| DELETE | `/api/reports/<id>/` | ✅ | Delete report |

---

## 🤖 AI Engine Overview (`ai_engine/ai_engine.py`)

### Emergency Detection
Scans user message for ~25 critical keywords (chest pain, heart attack, seizure…).
Responds immediately with 999/911 instructions — overrides all other logic.

### Disease Detection
Keyword matching against a structured knowledge base covering:
- Common **cold**, **cough**, **fever** (viral/bacterial)
- **Diabetes** (Type 1 & 2)
- **Heart disease** (coronary / heart failure)

### Response Generation
Each detected disease returns structured markdown with:
- 🥗 Diet recommendations
- 🏠 Home remedies
- 🏃 Lifestyle changes
- 💊 OTC medication suggestions
- 👨‍⚕️ Recommended specialist
- 🏥 "See a doctor if…" criteria

### BioBERT (`dmis-lab/biobert-base-cased-v1.1`)
Provides medical-domain text encoding via `encode_text()`.
Loaded lazily on first use; model cached in memory.

### T5-small summarisation
`summarise_text(text)` prefixes input with `"summarize: "` and generates
a concise summary (max 200 tokens) for medical report content.

---

## ⚠️ Limitations

- BioBERT embedding is available for future RAG integration; current chatbot uses rule-based matching.
- T5-small is a general-purpose model, not fine-tuned on medical corpora — summaries are informational.
- OCR accuracy depends on image quality and Tesseract installation.
- This system is for **academic and educational purposes only**.

---

## 🔮 Future Improvements

- Fine-tune BioBERT for medical entity recognition (NER).
- Implement vector-store RAG with FAISS for richer medical knowledge retrieval.
- Add appointment booking / doctor directory integration.
- Add multilingual support.
- Deploy with Nginx + Gunicorn for production.

---

## ⚠️ Medical Disclaimer

> **HealthChat is an informational tool only.** It does NOT provide medical diagnoses,
> prescriptions, or clinical advice. Always consult a qualified healthcare professional
> before making any medical decisions. In emergencies, call your local emergency number immediately.
