# 📚 AI PDF Chatbot Assistant

An intelligent, full-stack, and lightweight **AI Document Q&A and Chatbot System**. Upload PDF documents, inspect automatic executive summaries, and interact with the content through conversational question-answering backed by grounded page citations.

---

## 📌 Project Overview

The **AI PDF Chatbot Assistant** is a modern document question-answering platform that enables users to upload reports, academic papers, textbooks, and technical manuals. It extracts page-by-page text, indexes chunks for semantic context retrieval, generates structured executive summaries, and answers questions with precise source citations.

The application follows a decoupled **API-driven architecture** separating the **Streamlit** user interface from the **FastAPI** AI engine, with document metadata, extracted pages, and chat history persistently stored in an embedded **SQLite** database.

---

## 🎯 Project Objectives

> *"To provide a clean, fast, and user-friendly AI assistant for interrogating PDF documents with grounded source citations, instant executive summaries, and persistent conversation history."*

---

## 🚀 Key Features

* **📄 PDF Parsing & Page Extraction:** Extracts and structures text page-by-page using `pypdf`, tracking page numbers for citations.
* **🔍 Contextual Retrieval (RAG):** Ranks and retrieves the most relevant document chunks based on user queries, minimizing hallucinations.
* **📑 Source Citations & References:** Every response identifies the exact source pages (`[Page X]`) and includes readable excerpts.
* **📋 Automatic Executive Summarization:** Generates high-level document overviews, key findings, and highlights upon upload.
* **💬 Conversational Multi-Session Chat:** Create multiple conversation threads per document and switch between them seamlessly.
* **💾 Persistent SQLite Storage:** All uploaded documents, extracted pages, sessions, and messages are automatically saved in `data/chatbot.db`.
* **⚡ Dual-Mode AI Execution:**
  * **Live AI Mode:** Generates responses using Google Gemini API (`gemini-1.5-flash` / `gemini-pro`).
  * **Intelligent Offline Demo Mode:** If an API key is not provided, the system synthesizes answers from top-ranked document chunks so demos and tests never crash.
* **🎨 Modern Streamlit UI:** Features a dark-themed responsive layout with message bubbles, collapsible citations, and sidebar document management.

---

## 🛠️ Technologies Used

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ / 3.11+ | Core programming language |
| **Backend API** | FastAPI | High-performance RESTful API endpoints |
| **ASGI Server** | Uvicorn | Asynchronous web server |
| **Frontend** | Streamlit | Interactive web application UI |
| **Database** | SQLite3 | Embedded database for documents and chat history |
| **PDF Extraction** | PyPDF | Page-level text extraction and parsing |
| **AI / LLM** | Google Gemini API | Conversational reasoning and document summarization |
| **Data Validation** | Pydantic v2 | Request/response data validation |
| **Testing** | Pytest & TestClient | Automated unit and integration testing |

---

## 📐 System Architecture

```text
       ┌────────────────────────┐
       │   User / Web Browser   │
       └───────────┬────────────┘
                   │
                   ▼
       ┌────────────────────────┐
       │   Streamlit Frontend   │  (Port 8501)
       │    (frontend/app.py)   │
       └───────────┬────────────┘
                   │  HTTP REST (JSON & Multipart)
                   ▼
       ┌────────────────────────┐
       │    FastAPI Backend     │  (Port 8000)
       │   (backend/main.py)    │
       └─────┬────────────┬─────┘
             │            │
             ▼            ▼
┌──────────────────┐  ┌──────────────────┐
│ PDF & AI Engine  │  │ SQLite Database  │
│(pdf_processor.py,│  │  (chatbot.db)    │
│  ai_engine.py)   │  │  & uploads/      │
└──────────────────┘  └──────────────────┘
```

---

## 📂 Project Structure

```text
ai-pdf-chatbot/
│
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI REST endpoints & lifecycle
│   ├── pdf_processor.py     # PDF text extraction, chunking & citation retrieval
│   ├── ai_engine.py         # Google Gemini integration & offline synthesizer
│   └── database.py          # SQLite schema, document storage & chat persistence
│
├── frontend/
│   ├── __init__.py
│   └── app.py               # Streamlit web interface & citation cards
│
├── data/
│   ├── chatbot.db           # SQLite database (auto-created on startup)
│   └── uploads/             # Directory storing uploaded PDF files
│
├── tests/
│   └── test_api.py          # Pytest automated test suite
│
├── .env.example             # Template for optional GEMINI_API_KEY
├── requirements.txt         # Minimal, robust project dependencies
├── README.md                # Comprehensive project documentation
└── run_app.bat              # One-click startup script for Windows
```

---

## 🚦 Getting Started

### 1. Prerequisites
* Python 3.10, 3.11, or 3.12 installed.

### 2. Installation
Clone or navigate to the project directory, then install the dependencies:
```bash
pip install -r requirements.txt
```

### 3. (Optional) Configure Gemini API Key
To enable live generative responses with Google Gemini:
1. Obtain a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Create a `.env` file from the example:
   ```bash
   copy .env.example .env
   ```
3. Set your key:
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   ```
*(Note: You can also enter the API key directly into the Streamlit sidebar, or leave it empty to use the intelligent offline demo mode).*

---

## ▶️ Running the Application

### Option A: One-Click Windows Launch (Recommended)
Double-click `run_app.bat` or run it from command prompt:
```cmd
run_app.bat
```
This automatically starts:
* **FastAPI Backend:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Streamlit Frontend:** [http://localhost:8501](http://localhost:8501)

### Option B: Manual Launch (Two Terminals)

**Terminal 1 — Backend:**
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
python -m streamlit run frontend/app.py --server.port 8501
```

---

## 📖 API Endpoints Reference

Once the backend is running, interactive Swagger API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | API health and service status |
| `POST` | `/api/upload` | Upload `.pdf` file, extract pages, generate summary |
| `GET` | `/api/documents` | List all uploaded PDF documents |
| `GET` | `/api/documents/{doc_id}` | Retrieve document details and summary |
| `GET` | `/api/summary/{doc_id}` | Retrieve or refresh document executive summary |
| `POST` | `/api/chat` | Send question and get answer with page citations |
| `POST` | `/api/sessions` | Create a new conversation session for a document |
| `GET` | `/api/sessions` | List all conversation sessions |
| `GET` | `/api/history/{session_id}` | Get complete message history for a session |
| `DELETE` | `/api/sessions/{session_id}`| Delete a chat session and its messages |

---

## 🧪 Running Automated Tests

Run the full automated test suite using `pytest`:
```bash
pytest tests/test_api.py -v
```
All tests verify PDF ingestion, text extraction, question answering with citations, and session persistence in SQLite.

---

## 📜 License & Acknowledgments
Developed for educational demonstration, college project presentations, and practical document AI assistance.
