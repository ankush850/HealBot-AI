# 🩺 HealBot AI

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?style=for-the-badge&logo=streamlit" alt="Streamlit" />
  <img src="https://img.shields.io/badge/LangGraph-StateGraph-purple?style=for-the-badge" alt="LangGraph" />
  <img src="https://img.shields.io/badge/FAISS-VectorStore-orange?style=for-the-badge" alt="FAISS" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

<p align="center">
  <strong>HealBot AI</strong> is an intelligent, multi-agent healthcare platform engineered for real-time medical symptom analysis, emergency triage scoring, automated doctor appointment scheduling, and rapid disaster/epidemic alert broadcasting.
</p>

---

## 📑 Table of Contents
- [✨ Key Features](#-key-features)
- [🏛️ System Architecture](#️-system-architecture)
- [🤖 Multi-Agent Ecosystem](#-multi-agent-ecosystem)
- [📂 Project Structure](#-project-structure)
- [🛠️ Tech Stack](#️-tech-stack)
- [🚀 Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
  - [Database Initialization](#database-initialization)
- [🖥️ Running the Application](#️-running-the-application)
- [📡 API Documentation](#-api-documentation)
- [🧪 Simulation Engine](#-simulation-engine)
- [📱 WhatsApp Integration](#-whatsapp-integration)
- [⚠️ Medical Disclaimer](#️-medical-disclaimer)
- [📄 License](#-license)

---

## ✨ Key Features

- **🧠 Multi-Agent RAG Health Advisory:** Evaluates patient symptoms using LangGraph workflows, vector similarity search (FAISS), and medical knowledge graphs to generate evidence-based health guidance.
- **🚨 Emergency Triage & Scoring:** Automatically classifies emergencies into **CRITICAL**, **HIGH**, and **MODERATE** severity levels with vital sign checks and immediate action recommendations.
- **📅 Autonomous Doctor Booking:** Matches medical specialties, queries available doctor slots in real-time, validates time collisions, and secures appointment confirmations.
- **📊 Real-time Streamlit Dashboard:** Live operations dashboard featuring animated CSS alert pulses, triage statistics, active alert feeds, and one-click disaster/outbreak simulations.
- **📱 WhatsApp Alerts & Notifications:** Direct WhatsApp messaging pipeline for instant emergency SOS dispatches and appointment receipts.
- **⚡ High-Performance FastAPI Backend:** Asynchronous API with rate-limiting, session state lifecycle management, CORS middleware, and GZip compression.

---

## 🏛️ System Architecture

```
                       +-------------------------------+
                       |   Streamlit Web Dashboard     |
                       |  (Chat UI + Emergency Feeds)  |
                       +---------------+---------------+
                                       |
                                HTTP / REST API
                                       |
                       +---------------+---------------+
                       |       FastAPI Backend         |
                       |  (Session Manager & Router)   |
                       +---------------+---------------+
                                       |
          +----------------------------+----------------------------+
          |                            |                            |
+---------v----------+     +-----------v-----------+     +----------v----------+
| Health Adviser     |     | Emergency Triage      |     | Booking Agent       |
| Agent (LangGraph)  |     | Agent (StateGraph)    |     | (Slot Manager)      |
+---------+----------+     +-----------+-----------+     +----------+----------+
          |                            |                            |
          | RAG Search                 | SOS Dispatch               | Slot Query
          v                            v                            v
+--------------------+     +-----------------------+     +---------------------+
| FAISS Vector Store |     | WhatsApp Cloud API    |     | SQLite Database     |
| & Embeddings       |     | & Emergency Cache     |     | (diseases.db)       |
+--------------------+     +-----------------------+     +---------------------+
```

---

## 🤖 Multi-Agent Ecosystem

### 1. Health Adviser Agent (`agents/health_adviser.py`)
- Coordinates multi-turn patient dialogue using LangGraph state graphs.
- Retrieves disease knowledge and symptoms using FAISS dense vector retrieval.
- Formulates differential diagnoses, lifestyle precautions, and red-flag alerts.

### 2. Emergency Agent (`agents/emergency_agent.py`)
- Analyzes reports for epidemic outbreaks, mass-casualty incidents, and acute medical emergencies.
- Computes vulnerability indices and generates real-time public emergency banners.
- Broadcasts automated alerts to local emergency response teams.

### 3. Doctor Booking Agent (`agents/booking_agent.py`)
- Identifies the required medical specialty based on consultation context.
- Retrieves available hospital slots and handles booking, rescheduling, and cancellations.
- Formats structured appointment confirmations for SMS and WhatsApp dispatch.

---

## 📂 Project Structure

```
health_agent/
├── agents/                      # LangGraph & AI Agent definitions
│   ├── booking_agent.py         # Autonomous doctor appointment scheduling
│   ├── emergency_agent.py       # Triage scoring & disaster alert system
│   ├── health_adviser.py        # RAG-powered symptom & disease analysis
│   └── run_simulations.py       # Outbreak and casualty simulation engine
├── tools/                       # Reusable utility modules and adapters
│   ├── emergency_tools.py       # Triage algorithms and alert cache
│   ├── sql_tools.py             # SQLite ORM and slot query helpers
│   ├── whatsapp_tools.py        # WhatsApp Cloud API messaging client
│   └── mongo_tools.py           # Consultation storage adapter
├── faiss_index/                 # FAISS vector database indices
├── scripts/                     # Data ingestion and initialization scripts
│   └── ingest_data.py           # Medical document embedding builder
├── app.py                       # Streamlit UI Dashboard
├── main.py                      # FastAPI Backend server
├── create_diseases_db.sql       # Database schema definition
├── diseases.db                  # SQLite database (diseases & hospital slots)
├── emergency_db_cache.json      # In-memory emergency reference cache
├── requirements.txt             # Project Python dependencies
└── README.md                    # Project documentation
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/), Uvicorn, Pydantic v2 |
| **Frontend Framework** | [Streamlit](https://streamlit.io/), Plotly Express |
| **Agent Framework** | [LangChain](https://www.langchain.com/), [LangGraph](https://langchain-ai.github.io/langgraph/) |
| **LLM & Embeddings** | OpenAI GPT-4o / GPT-3.5-Turbo, HuggingFace Sentence Transformers |
| **Vector Database** | [FAISS (Facebook AI Similarity Search)](https://github.com/facebookresearch/faiss) |
| **Relational Database** | SQLite3 |
| **Integrations** | WhatsApp Business API, Requests, Python-dotenv |

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+** installed on your system.
- An **OpenAI API Key** ([Get your key here](https://platform.openai.com/api-keys)).
- *(Optional)* WhatsApp Business API credentials for live messaging.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ankush850/HealBot-AI-.git
   cd HealBot-AI-
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

### Environment Configuration

Create a `.env` file in the root directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
HEALTH_MODEL_NAME=gpt-4o
HEALTH_MODEL_TEMPERATURE=0

# Server Configuration
PORT=8000
DEBUG=true
CORS_ORIGINS=*
RATE_LIMIT_PER_MINUTE=60

# WhatsApp API Configuration (Optional)
WHATSAPP_API_KEY=your_whatsapp_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
```

---

### Database Initialization

To build the SQLite medical schema and vector embeddings:

```bash
# Initialize SQLite Database
python sql_script.py

# Ingest Medical Knowledge into FAISS Vector Store
python scripts/ingest_data.py
```

---

## 🖥️ Running the Application

### 1. Launch FastAPI Backend
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
- API Root: `http://127.0.0.1:8000`
- Interactive Swagger Docs: `http://127.0.0.1:8000/docs`

### 2. Launch Streamlit Dashboard (In a separate terminal)
```bash
streamlit run app.py
```
- Dashboard UI will open at: `http://localhost:8501`

---

## 📡 API Documentation

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/status` | Check system status and emergency mode flag |
| `POST` | `/emergency/toggle` | Toggle system-wide emergency mode ON/OFF |
| `GET` | `/alerts/current` | Retrieve list of active emergency alerts |
| `POST` | `/emergency/process` | Submit and evaluate an urgent emergency report |
| `POST` | `/simulation/run/{type}` | Run an emergency simulation (`outbreak` or `disaster`) |
| `GET` | `/simulation/status` | Get simulation metrics and database counts |
| `POST` | `/simulation/reset` | Clear simulation events and active alerts |

### Example: Process Emergency Report
```bash
curl -X POST "http://127.0.0.1:8000/emergency/process" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Multiple people showing acute respiratory failure in Hanamkonda area",
       "session_id": "session-101"
     }'
```

---

## 🧪 Simulation Engine

HealBot AI includes a built-in simulation engine for training and emergency preparedness:
- **Outbreak Simulation:** Generates synthetic cluster outbreaks to test epidemic metrics and alert dispatchers.
- **Disaster Simulation:** Simulates mass casualties, structural collapses, and automated triage priority queues.

You can trigger simulations directly from the **🚨 Emergency Dashboard** tab in the Streamlit UI or via the `/simulation/run/outbreak` API.

---

## 📱 WhatsApp Integration

HealBot AI supports automated patient communication through the WhatsApp Cloud API:
- Automatic appointment confirmations and reminders.
- Direct SOS escalation messages to registered emergency contacts.
- Quick health advice delivery for low-bandwidth mobile users.

---

## ⚠️ Medical Disclaimer

> **IMPORTANT:** HealBot AI is designed to assist with triage routing, educational symptom information, and operational scheduling. It is **not** a substitute for professional medical advice, clinical diagnosis, or emergency rescue services. In life-threatening scenarios, always contact local emergency services immediately (e.g., **108 / 112** in India or **911** in the US).

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more details.

---

<p align="center">
  Built with ❤️ for better, accessible, and faster emergency healthcare.
</p>
