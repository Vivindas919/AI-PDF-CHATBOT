"""
FastAPI application for AI PDF Chatbot.
Provides RESTful endpoints for PDF upload, question-answering with citations,
document summarization, and chat session history management.
"""

import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.database import (
    init_db,
    save_document,
    get_document,
    get_all_documents,
    get_document_pages,
    update_document_summary,
    create_session,
    get_session,
    get_all_sessions,
    delete_session,
    save_message,
    get_session_messages,
    UPLOADS_DIR
)
from backend.pdf_processor import extract_text_from_pdf
from backend.ai_engine import answer_question, generate_document_summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database tables and storage folders on API startup."""
    init_db()
    yield


# Initialize FastAPI application
app = FastAPI(
    title="AI PDF Chatbot API",
    description="High-performance backend API for intelligent PDF document Q&A and conversation history.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local development and Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Request & Response Models
# ---------------------------------------------------------

class ChatRequest(BaseModel):
    doc_id: str = Field(..., description="Target document ID")
    session_id: str = Field(..., description="Unique chat session ID")
    message: str = Field(..., min_length=1, description="User question or query")
    api_key: Optional[str] = Field(None, description="Optional Google Gemini API key")


class CreateSessionRequest(BaseModel):
    doc_id: str = Field(..., description="Document ID to associate with this session")
    title: Optional[str] = Field("New Chat", description="Session title")


# ---------------------------------------------------------
# REST API Endpoints
# ---------------------------------------------------------

@app.get("/")
def root():
    """API Health and information endpoint."""
    return {
        "status": "online",
        "service": "AI PDF Chatbot API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Uploads a PDF file, parses text page-by-page, generates an initial summary,
    and registers it in the SQLite database.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported.")

    doc_id = f"doc_{uuid.uuid4().hex[:10]}"
    safe_filename = os.path.basename(file.filename)
    dest_path = os.path.join(UPLOADS_DIR, f"{doc_id}_{safe_filename}")

    try:
        content = await file.read()
        with open(dest_path, "wb") as f:
            f.write(content)

        total_pages, pages_data = extract_text_from_pdf(dest_path)
        if total_pages == 0:
            raise HTTPException(status_code=400, detail="The PDF file contains no pages.")

        # Generate initial document summary
        summary = generate_document_summary(pages_data)

        # Save to database
        save_document(
            doc_id=doc_id,
            filename=safe_filename,
            file_path=dest_path,
            page_count=total_pages,
            pages_data=pages_data,
            summary=summary
        )

        # Create an initial default session for this document
        session_id = f"sess_{uuid.uuid4().hex[:10]}"
        create_session(session_id=session_id, doc_id=doc_id, title=f"Chat: {safe_filename[:25]}")

        return {
            "success": True,
            "doc_id": doc_id,
            "filename": safe_filename,
            "page_count": total_pages,
            "summary": summary,
            "session_id": session_id
        }

    except Exception as e:
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except OSError:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@app.get("/api/documents")
def list_documents():
    """Returns a list of all uploaded PDF documents."""
    return {"documents": get_all_documents()}


@app.get("/api/documents/{doc_id}")
def get_document_details(doc_id: str):
    """Retrieves document details and summary."""
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@app.get("/api/summary/{doc_id}")
def get_or_refresh_summary(doc_id: str, api_key: Optional[str] = None):
    """Retrieves or refreshes the executive summary for a document."""
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    pages = get_document_pages(doc_id)
    summary = generate_document_summary(pages, api_key=api_key)
    update_document_summary(doc_id, summary)
    return {"doc_id": doc_id, "summary": summary}


@app.post("/api/chat")
def chat_with_pdf(req: ChatRequest):
    """
    Processes a chat query over the target PDF document.
    Saves user message, retrieves relevant page citations, generates answer,
    and logs assistant response in SQLite.
    """
    doc = get_document(req.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Ensure session exists or create it
    session = get_session(req.session_id)
    if not session:
        create_session(req.session_id, req.doc_id, title="Chat Session")

    # Save user message
    save_message(req.session_id, role="user", content=req.message)

    # Get document pages
    pages = get_document_pages(req.doc_id)
    if not pages:
        raise HTTPException(status_code=400, detail="Document contains no readable pages.")

    # Get prior chat history for context
    history = get_session_messages(req.session_id)

    # Answer question
    result = answer_question(
        query=req.message,
        pages=pages,
        chat_history=history,
        api_key=req.api_key
    )

    # Save assistant message with citations
    save_message(
        session_id=req.session_id,
        role="assistant",
        content=result["answer"],
        citations=result.get("citations", [])
    )

    return {
        "answer": result["answer"],
        "citations": result.get("citations", []),
        "session_id": req.session_id,
        "mode": result.get("mode", "standard")
    }


@app.post("/api/sessions")
def create_new_session(req: CreateSessionRequest):
    """Creates a new conversation session for a document."""
    doc = get_document(req.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    session = create_session(session_id, req.doc_id, req.title or "New Chat")
    return session


@app.get("/api/sessions")
def list_sessions():
    """Lists all conversation sessions."""
    return {"sessions": get_all_sessions()}


@app.get("/api/history/{session_id}")
def get_history(session_id: str):
    """Retrieves all chat messages for a given session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    messages = get_session_messages(session_id)
    return {"session_id": session_id, "messages": messages}


@app.delete("/api/sessions/{session_id}")
def delete_chat_session(session_id: str):
    """Deletes a session and its message history."""
    success = delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"success": True, "deleted_session_id": session_id}
