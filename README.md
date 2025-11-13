# 🩺 HealBot AI

**HealBot AI** is an advanced AI-powered Health Advisory, Emergency Triage, and Hospital Appointment Booking system.

---

## 🌟 Key Features

- **💬 AI Health Advisory:** Symptom analysis, medical queries, and proactive health recommendations.
- **🚨 Emergency Response & Triage:** Real-time emergency detection, severity classification (Critical, High, Moderate), and automated alerts.
- **📅 Doctor & Appointment Booking:** Multi-agent coordination for finding doctors and booking appointments.
- **📊 Real-time Dashboard:** Streamlit-powered dashboard for alerts, simulations, and live operations.

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/ankush850/HealBot-AI-.git
cd HealBot-AI-
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file with your credentials:
```env
OPENAI_API_KEY=your_openai_api_key
WHATSAPP_API_KEY=your_whatsapp_api_key
```

### 3. Run Backend API
```bash
uvicorn main:app --reload --port 8000
```

### 4. Run Streamlit Dashboard
```bash
streamlit run app.py
```

<!-- update: feat(api): scaffold FastAPI application and route registry -->

<!-- update: test: add mock scenarios for critical emergency alerts -->

<!-- update: style: adjust Streamlit sidebar styling and branding -->

<!-- update: perf: reduce memory footprint of loaded FAISS indices -->

<!-- update: perf: implement in-memory caching for frequently queried conditions -->

<!-- update: feat(agent): add multi-language support hooks for patient advisory -->

<!-- update: feat(agent): add medication reminder and regimen guidance -->

<!-- update: fix(emergency): fix alert deduplication window logic -->

<!-- update: test: benchmark vector search performance against large query sets -->

<!-- update: feat(agent): add vaccination schedule lookups -->

<!-- update: perf: minimize memory allocations during batch simulation runs -->
