# Ustaad-AI 🛠️🤖

[![Download APK](https://img.shields.io/badge/Download-Android%20APK-green?style=for-the-badge&logo=android)](https://github.com/abdulhayykhan/Ustaad-AI/releases/download/v1.0.0/frontend.apk)

**Ustaad-AI** is a premium, fully-orchestrated AI service platform tailored for the informal economy in Karachi, Pakistan. The platform leverages Google's Gemini models to translate complex, natural language requests (often in Roman Urdu) into highly specific vendor matches, factoring in geolocation, pricing, urgency, and historic ratings via a dynamic 6-factor matchmaking algorithm.

## Features ✨
- **Multimodal Flet UI:** A heavily customized, mobile-responsive Flet frontend (v0.85+) featuring smooth animations, an interactive Dark Mode, and deep-linking into WhatsApp and Google Maps.
- **Async Orchestration:** A FastAPI backend driving multi-agent pipelines (Intent Parsing, Matching, Pricing) securely behind rate limit guards and resilient mock fallbacks.
- **Live Debug Traces:** Integrated SSE endpoint that streams the raw algorithmic reasoning directly to an expandable debug view in the user's dashboard.
- **Voice Simulator:** A native inline state mutation that visually mocks an interactive voice-to-text input flow without freezing the application thread.

## Architecture 🏛️
- **Frontend:** Flet (`flet>=0.85.0`)
- **Backend:** FastAPI, Uvicorn
- **AI Core:** Google Generative AI (`gemini-2.0-flash`)
- **Database:** SQLite (via SQLAlchemy)
- **Geolocation:** Google Maps API (`googlemaps`)

## Getting Started 🚀

### 1. Environment Setup
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_MAPS_API_KEY=your_gmaps_api_key
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize the Database
Seed the 500 mock Karachi service providers into the local SQLite database:
```bash
python -m backend.seed
```

### 4. Run the Application
You will need two terminal sessions.

**Terminal 1 (FastAPI Backend):**
```bash
uvicorn backend.main:app --reload
```

**Terminal 2 (Flet Frontend):**
```bash
python -m frontend.main
```

## Hackathon Demo Flow 🎤
1. Ensure the backend is running.
2. Launch the Flet UI. Toggle between **Light** and **Dark Mode** to show off semantic UI components.
3. Click the **Microphone** icon to run the simulated Voice Note payload.
4. Hit **Send** to trigger the AI pipeline. Observe the dynamic multi-stage loading animation.
5. Review the **Debug Traces** in the ExpansionTile to see the 6-factor algorithm logs.
6. Check out the **Google Maps** and **WhatsApp** deep-links rendered perfectly in the response bubble!

---
*Built with ❤️ for the AI Seekho 2026 Antigravity Hackathon.*
