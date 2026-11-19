"""
Streamlit Web Application for AI PDF Chatbot.
Provides an interactive user interface for uploading PDF documents,
viewing document summaries, chatting with the document, and reviewing page citations.
"""

import os
import requests
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="AI PDF Chatbot",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# Custom Styling
st.markdown(
    """
    <style>
    /* Global Container Adjustments */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    
    /* Header card */
    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        border: 1px solid #334155;
    }
    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .main-header p {
        margin: 0.3rem 0 0 0;
        color: #94a3b8;
        font-size: 1rem;
    }

    /* Citation badge */
    .citation-badge {
        display: inline-block;
        background-color: #3b82f6;
        color: white;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.3rem;
    }
    
    /* Metadata chip */
    .meta-chip {
        display: inline-block;
        background-color: #334155;
        color: #cbd5e1;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.8rem;
        margin-right: 0.5rem;
    }

    /* Summary Card */
    .summary-box {
        background-color: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 1rem 1.25rem;
        border-radius: 0 8px 8px 0;
        color: #1e293b;
        margin-bottom: 1.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# Helper Functions for Backend API Calls
# ---------------------------------------------------------

def check_backend_health() -> bool:
    try:
        r = requests.get(f"{API_BASE_URL}/", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def fetch_documents():
    try:
        r = requests.get(f"{API_BASE_URL}/api/documents", timeout=5)
        if r.status_code == 200:
            return r.json().get("documents", [])
    except Exception:
        pass
    return []


def fetch_sessions():
    try:
        r = requests.get(f"{API_BASE_URL}/api/sessions", timeout=5)
        if r.status_code == 200:
            return r.json().get("sessions", [])
    except Exception:
        pass
    return []


def fetch_history(session_id: str):
    try:
        r = requests.get(f"{API_BASE_URL}/api/history/{session_id}", timeout=5)
        if r.status_code == 200:
            return r.json().get("messages", [])
    except Exception:
        pass
    return []


def upload_pdf_file(uploaded_file):
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
        r = requests.post(f"{API_BASE_URL}/api/upload", files=files, timeout=60)
        if r.status_code == 200:
            return r.json()
        else:
            st.sidebar.error(f"Upload failed: {r.json().get('detail', 'Unknown error')}")
    except Exception as e:
        st.sidebar.error(f"Error connecting to backend: {str(e)}")
    return None


def send_chat_message(doc_id: str, session_id: str, message: str, api_key: str = None):
    try:
        payload = {
            "doc_id": doc_id,
            "session_id": session_id,
            "message": message,
            "api_key": api_key if api_key else None
        }
        r = requests.post(f"{API_BASE_URL}/api/chat", json=payload, timeout=60)
        if r.status_code == 200:
            return r.json()
        else:
            st.error(f"Chat error: {r.json().get('detail', 'Failed to generate answer')}")
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
    return None


def create_new_session_api(doc_id: str, title: str = "New Chat"):
    try:
        payload = {"doc_id": doc_id, "title": title}
        r = requests.post(f"{API_BASE_URL}/api/sessions", json=payload, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def delete_session_api(session_id: str):
    try:
        r = requests.delete(f"{API_BASE_URL}/api/sessions/{session_id}", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def refresh_summary_api(doc_id: str, api_key: str = None):
    try:
        params = {"api_key": api_key} if api_key else {}
        r = requests.get(f"{API_BASE_URL}/api/summary/{doc_id}", params=params, timeout=30)
        if r.status_code == 200:
            return r.json().get("summary", "")
    except Exception:
        pass
    return None


# ---------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------

with st.sidebar:
    st.title("⚙️ AI Configuration")
    api_key_input = st.text_input(
        "Google Gemini API Key (Optional)",
        type="password",
        help="Enter your Gemini API key, or leave blank to use the .env key / offline demo synthesizer."
    )

    st.markdown("---")
    st.subheader("📄 Upload Document")
    pdf_upload = st.file_uploader("Select PDF file", type=["pdf"], key="pdf_file_uploader")
    
    if pdf_upload is not None:
        if st.button("📤 Process PDF", use_container_width=True, type="primary"):
            with st.spinner("Extracting text and analyzing PDF..."):
                res = upload_pdf_file(pdf_upload)
                if res and res.get("success"):
                    st.success(f"Uploaded: {res['filename']} ({res['page_count']} pages)")
                    st.session_state["active_doc_id"] = res["doc_id"]
                    st.session_state["active_session_id"] = res["session_id"]
                    st.rerun()

    st.markdown("---")
    st.subheader("📂 Document Library")
    documents = fetch_documents()

    if documents:
        doc_names = {d["doc_id"]: f"{d['filename']} ({d['page_count']} pgs)" for d in documents}
        default_idx = 0
        if "active_doc_id" in st.session_state:
            ids = list(doc_names.keys())
            if st.session_state["active_doc_id"] in ids:
                default_idx = ids.index(st.session_state["active_doc_id"])

        selected_doc_id = st.selectbox(
            "Active Document",
            options=list(doc_names.keys()),
            format_func=lambda x: doc_names[x],
            index=default_idx
        )
        st.session_state["active_doc_id"] = selected_doc_id

        # Sessions for this document
        st.markdown("---")
        st.subheader("💬 Chat Sessions")
        col_new, col_del = st.columns([1, 1])
        
        with col_new:
            if st.button("➕ New Chat", use_container_width=True):
                new_sess = create_new_session_api(selected_doc_id)
                if new_sess:
                    st.session_state["active_session_id"] = new_sess["session_id"]
                    st.rerun()

        all_sessions = fetch_sessions()
        doc_sessions = [s for s in all_sessions if s["doc_id"] == selected_doc_id]

        if doc_sessions:
            sess_map = {s["session_id"]: f"{s['title']} ({s['created_at'][11:16]})" for s in doc_sessions}
            sess_idx = 0
            if "active_session_id" in st.session_state and st.session_state["active_session_id"] in sess_map:
                sess_idx = list(sess_map.keys()).index(st.session_state["active_session_id"])
            
            selected_sess_id = st.selectbox(
                "Conversation",
                options=list(sess_map.keys()),
                format_func=lambda x: sess_map[x],
                index=sess_idx
            )
            st.session_state["active_session_id"] = selected_sess_id

            with col_del:
                if st.button("🗑️ Delete", use_container_width=True):
                    delete_session_api(selected_sess_id)
                    st.session_state.pop("active_session_id", None)
                    st.rerun()
        else:
            # Auto-create session if none exists
            if "active_session_id" not in st.session_state:
                new_sess = create_new_session_api(selected_doc_id)
                if new_sess:
                    st.session_state["active_session_id"] = new_sess["session_id"]
                    st.rerun()
    else:
        st.info("No documents uploaded yet. Upload a PDF above to get started.")

    st.markdown("---")
    backend_status = check_backend_health()
    if backend_status:
        st.caption("🟢 Backend API: **Online** (Port 8000)")
    else:
        st.caption("🔴 Backend API: **Offline** (Run `run_app.bat`)")


# ---------------------------------------------------------
# Main Chat Area
# ---------------------------------------------------------

# Main Header Banner
st.markdown(
    """
    <div class="main-header">
        <h1>📚 AI PDF Chatbot</h1>
        <p>Upload any PDF document, inspect executive summaries, and ask questions with grounded page citations.</p>
    </div>
    """,
    unsafe_allow_html=True
)

active_doc_id = st.session_state.get("active_doc_id")
active_session_id = st.session_state.get("active_session_id")

if not active_doc_id:
    # Empty State Guide
    st.info("👋 Welcome! Please upload a PDF document in the sidebar to begin.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 📄 1. Upload PDF")
        st.write("Upload reports, academic papers, technical manuals, or textbooks.")
    with col2:
        st.markdown("### 🧠 2. Instant Summary")
        st.write("Get an automatic executive breakdown and key findings right away.")
    with col3:
        st.markdown("### 💬 3. Chat with Citations")
        st.write("Ask natural questions and receive accurate answers with exact page references.")

else:
    # Fetch active document info
    active_doc = next((d for d in documents if d["doc_id"] == active_doc_id), None)
    
    if active_doc:
        # Document Stats Bar
        st.markdown(
            f"""
            <div>
                <span class="meta-chip">📁 <b>File:</b> {active_doc['filename']}</span>
                <span class="meta-chip">📑 <b>Pages:</b> {active_doc['page_count']}</span>
                <span class="meta-chip">🕒 <b>Uploaded:</b> {active_doc['upload_date']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # Document Executive Summary Expander
        with st.expander("📋 View Document Executive Summary", expanded=False):
            st.markdown(active_doc.get("summary") or "No summary available.")
            if st.button("🔄 Regenerate Summary with AI", key="btn_refresh_summary"):
                with st.spinner("Regenerating executive summary..."):
                    new_summary = refresh_summary_api(active_doc_id, api_key_input)
                    if new_summary:
                        active_doc["summary"] = new_summary
                        st.success("Summary refreshed!")
                        st.rerun()

    # Load and Render Chat Messages
    if active_session_id:
        messages = fetch_history(active_session_id)
        
        # Display message history
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # If assistant message has citations, render them
                if msg["role"] == "assistant" and msg.get("citations"):
                    citations = msg["citations"]
                    if isinstance(citations, list) and len(citations) > 0:
                        with st.expander(f"🔍 Source Citations ({len(citations)} references)"):
                            for cit in citations:
                                page_num = cit.get("page", "?")
                                snippet = cit.get("snippet", "")
                                st.markdown(f"**Page {page_num}:** *\"{snippet}\"*")

        # Chat Input Box
        user_prompt = st.chat_input("Ask a question about this document...")
        if user_prompt:
            # Display user message immediately
            with st.chat_message("user"):
                st.markdown(user_prompt)

            # Query backend
            with st.chat_message("assistant"):
                with st.spinner("Analyzing document context and synthesizing response..."):
                    resp = send_chat_message(
                        doc_id=active_doc_id,
                        session_id=active_session_id,
                        message=user_prompt,
                        api_key=api_key_input
                    )
                    if resp:
                        st.markdown(resp["answer"])
                        citations = resp.get("citations", [])
                        if citations:
                            with st.expander(f"🔍 Source Citations ({len(citations)} references)"):
                                for cit in citations:
                                    st.markdown(f"**Page {cit.get('page')}:** *\"{cit.get('snippet')}\"*")
            
            # Rerun to refresh history state
            st.rerun()
