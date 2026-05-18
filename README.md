# Ustaad-AI 🛠️🤖

[![Download APK](https://img.shields.io/badge/Download-Android%20APK-green?style=for-the-badge&logo=android)](https://github.com/abdulhayykhan/Ustaad-AI/releases/download/v1.0.0/frontend.apk)
[![Built for](https://img.shields.io/badge/Built%20for-AI%20Seekho%202026%20Antigravity%20Hackathon-blue?style=for-the-badge)](https://github.com/abdulhayykhan/Ustaad-AI)
[![Python](https://img.shields.io/badge/Python-3.11-yellow?style=for-the-badge&logo=python)](https://www.python.org/)
[![Gemini](https://img.shields.io/badge/AI%20Core-Gemini%202.0%20Flash-orange?style=for-the-badge&logo=google)](https://ai.google.dev/)

---

## What Is This?

**Ustaad-AI** is an AI-powered service worker discovery platform built for Karachi's informal economy. Users describe their problem in natural language — Roman Urdu, English, or Urdu — and the system finds, ranks, and books the best available local service worker automatically.

The platform runs a **3-agent orchestration pipeline** (Intent Parser → Matchmaker → Pricer) backed by a real SQLite database of 500 seeded Karachi service providers. Every agent decision is streamed live to the frontend via Server-Sent Events (SSE) so judges and users can verify the reasoning in real time.

---

## Features ✨

- **Roman Urdu / Urdu / English NLP** — Gemini parses noisy, multilingual, informal requests into structured intent (service type, location, urgency, time).
- **3-Agent Pipeline** — Intent Parser, Matchmaker, and Pricer run sequentially with structured JSON outputs validated by Pydantic schemas.
- **6-Factor Matching Algorithm** — Providers ranked by: Travel Time (30%), Rating (20%), Reliability (20%), Price (15%), Cancellation Rate (15%).
- **Real Geolocation** — Google Maps Geocoding + Distance Matrix API for actual driving distance and travel time, not mock values.
- **Dynamic Pricing** — Urgency multiplier (1.5× if high) + distance fee (50 PKR/km) on top of provider's base rate.
- **Live Agent Traces** — SSE endpoint streams raw orchestration logs to expandable debug view in the UI.
- **Voice Simulator** — Inline voice-to-text simulation without blocking the UI thread.
- **WhatsApp + Maps Deep Links** — One-tap contact and navigation directly from the result card.
- **Dark Mode** — Full light/dark theme toggle on the Flet frontend.
- **Android APK** — Built and released via GitHub Actions CI/CD (Flet `flet build apk`).
- **429 Fallback Handling** — All 3 agents have mock fallbacks if Gemini quota is exhausted mid-demo.

---

## Architecture 🏛️

```
User Input (Roman Urdu / English / Urdu)
        │
        ▼
┌─────────────────────────────────────────┐
│         FastAPI Backend (Uvicorn)        │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │     UstaadOrchestrator           │   │
│  │                                  │   │
│  │  1. Intent Parser Agent          │   │
│  │     └─ Gemini 2.0 Flash (JSON)   │   │
│  │                                  │   │
│  │  2. Matchmaker Agent             │   │
│  │     ├─ Google Maps Geocoding     │   │
│  │     ├─ SQLite DB Query           │   │
│  │     ├─ Distance Matrix API       │   │
│  │     └─ Gemini 2.0 Flash (Rank)   │   │
│  │                                  │   │
│  │  3. Pricer Agent                 │   │
│  │     └─ Gemini 2.0 Flash (JSON)   │   │
│  │                                  │   │
│  │  SSE Trace Queue (asyncio)       │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
        │                   │
        ▼                   ▼
  POST /api/request    GET /api/agent-traces
        │                   │
        ▼                   ▼
┌─────────────────────────────────────────┐
│         Flet Frontend (Mobile UI)        │
│  - Chat interface                        │
│  - Multi-stage loading animation         │
│  - Expandable SSE debug trace window     │
│  - WhatsApp + Maps deep links            │
└─────────────────────────────────────────┘
```

| Layer | Technology |
|-------|-----------|
| Frontend | Flet `>=0.85.0, <0.91.0` |
| Backend | FastAPI + Uvicorn |
| AI Core | Google Gemini 2.0 Flash (`google-genai`) |
| Database | SQLite via SQLAlchemy |
| Geolocation | Google Maps API (`googlemaps`) |
| Deployment | Cloud Run (backend), GitHub Actions (APK) |

---

## Getting Started 🚀

### Prerequisites

- Python 3.11
- A **Google Gemini API Key** — [get one here](https://aistudio.google.com/app/apikey)
- A **Google Maps API Key** with Geocoding + Distance Matrix enabled — [get one here](https://console.cloud.google.com/)

---

### 1. Clone the Repository

```bash
git clone https://github.com/abdulhayykhan/Ustaad-AI.git
cd Ustaad-AI
```

### 2. Create Environment File

```bash
cp .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** The package `google-genai` is required (not `google-generativeai`). The `requirements.txt` includes the correct package.

### 4. Seed the Database

Populate 500 mock Karachi service providers into the local SQLite DB:

```bash
python -m backend.seed
```

Expected output:
```
Starting database seeding...
Successfully seeded 500 providers to the database.
```

### 5. Run the Application

Open **two terminal sessions** from the project root:

**Terminal 1 — FastAPI Backend:**
```bash
uvicorn backend.main:app --reload
```
Backend runs on `http://localhost:8000`.

**Terminal 2 — Flet Frontend:**
```bash
python -m frontend.main
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/request` | Submit natural language service request. Triggers full 3-agent pipeline. |
| `GET` | `/api/agent-traces` | SSE stream of live agent reasoning logs. |

**Sample Request:**
```bash
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{"text": "Malir Halt mein kal subah AC mechanic chahiye, urgent hai"}'
```

---

## Sample Prompts

```
Mujhe kal subah Malir Halt mein AC technician chahiye, AC bilkul cooling nahi kar raha.

Yar Shah Faisal Number 3 mein urgent electrician chahiye, main board se dhuan nikal raha hai!

Sea View apartments ke paas kisi Generator Mechanic ka contact milega? Kal dopahar mein service karwani hai.

گلشن اقبال بلاک 13D میں واشنگ مشین کا ٹیکنیشن چاہیے۔ پانی لیک ہو رہا ہے۔

Need a plumber tomorrow morning at DHA Phase 6 Khayaban-e-Shahbaz. Kitchen sink completely clogged.
```

---

## Matching Algorithm

The Matchmaker Agent scores each candidate provider using this weighted formula:

| Factor | Weight | Source |
|--------|--------|--------|
| Travel Time | 30% | Google Maps Distance Matrix |
| Rating | 20% | Provider DB (`rating` field, 0–5) |
| Reliability Score | 20% | Provider DB (`reliability_score`, 0–100) |
| Base Rate (Price) | 15% | Provider DB (`base_rate_pkr`) |
| Cancellation Rate | 15% | Provider DB (`cancellation_rate`, 0–1) |

Lower travel time, higher rating, higher reliability, lower price, and lower cancellation rate = higher score.

---

## Dynamic Pricing Formula

```
Total = Base Rate
      + (Base Rate × 0.5)  [if urgency = "high"]
      + (Distance in km × 50 PKR)
```

**Example:** Base 800 PKR + Urgency 400 PKR + Distance (3.84 km × 50) 192 PKR = **1,392 PKR**

---

## Demo Flow 🎤

1. Ensure backend is running (`uvicorn backend.main:app --reload`).
2. Launch Flet UI (`python -m frontend.main`).
3. Toggle **Dark Mode** using the top-right icon.
4. Click the **Microphone** button — watch the simulated voice input populate.
5. Hit **Send** — observe the multi-stage loading animation:
   - 🤔 Ustaad-AI soch raha hai...
   - 🔍 Aas paas ustaad dhoond raha hai...
   - 💰 Bhau taal tay kar raha hai...
   - ✅ Booking final kar raha hai...
6. Expand **"View AI Agent Reasoning"** to see live SSE traces from all 3 agents.
7. View the result card: provider name, distance, pricing breakdown.
8. Tap **"Message Ustaad on WhatsApp"** and **📍 Distance** links.

---

## Project Structure

```
Ustaad-AI/
├── backend/
│   ├── agents.py        # UstaadOrchestrator + 3 sub-agents
│   ├── database.py      # SQLAlchemy engine + session config
│   ├── main.py          # FastAPI app, routes, SSE endpoint
│   ├── models.py        # Provider + Booking ORM models
│   ├── seed.py          # 500-provider Karachi DB seeder
│   └── tools.py         # Google Maps geocoding + distance tools
├── frontend/
│   └── main.py          # Flet mobile UI
├── .github/
│   └── workflows/
│       └── build-apk.yml  # GitHub Actions APK builder
├── .env.example
├── Dockerfile
├── requirements.txt
└── sample_prompts.txt
```

---

## Deployment

### Backend (Cloud Run)

```bash
docker build -t ustaad-ai .
docker run -p 8080:8080 --env-file .env ustaad-ai
```

Live backend: `https://ustaad-ai-620054685556.europe-west1.run.app`

### Android APK (GitHub Actions)

Push to `main` branch — the workflow in `.github/workflows/build-apk.yml` automatically builds and uploads the APK artifact. Download from the [Releases](https://github.com/abdulhayykhan/Ustaad-AI/releases) page.

---

## 📄 License

This project is open-source and available for educational and commercial use under the MIT License.

---

**Made with ❤️ by [Abdul Hayy Khan](https://www.linkedin.com/in/abdulhayykhan/)**