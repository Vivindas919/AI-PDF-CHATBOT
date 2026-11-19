"""
Test suite for AI PDF Chatbot API.
Tests PDF processing, document ingestion, executive summarization,
conversational question answering with citations, and session management.
"""

import io
import os
import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from backend.main import app
from backend.database import init_db

client = TestClient(app)


def generate_sample_pdf_bytes() -> bytes:
    """Generates an in-memory 2-page sample PDF for automated testing."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    
    # Page 1
    c.drawString(72, 720, "Artificial Intelligence and Machine Learning Report")
    c.drawString(72, 690, "Section 1: Foundations of Deep Learning")
    c.drawString(72, 660, "Artificial intelligence involves training computational algorithms to learn patterns.")
    c.drawString(72, 630, "Neural networks use backpropagation and gradient descent for parameter optimization.")
    c.drawString(72, 600, "Key finding: Transformer architectures achieved state-of-the-art results in NLP.")
    c.showPage()
    
    # Page 2
    c.drawString(72, 720, "Section 2: Retrieval Augmented Generation (RAG)")
    c.drawString(72, 690, "RAG combines parametric memory with external knowledge retrieval mechanisms.")
    c.drawString(72, 660, "Documents are indexed by extracting page text, chunking, and ranking relevance.")
    c.drawString(72, 630, "Citation accuracy ensures hallucinations are minimized during technical question answering.")
    c.showPage()
    
    c.save()
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database schema is fresh before running tests."""
    init_db()


def test_root_endpoint():
    """Test API health and welcome endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "AI PDF Chatbot API" in data["service"]


def test_upload_non_pdf_fails():
    """Test that uploading non-PDF files is rejected with HTTP 400."""
    response = client.post(
        "/api/upload",
        files={"file": ("notes.txt", b"plain text content", "text/plain")}
    )
    assert response.status_code == 400
    assert "Only PDF files" in response.json()["detail"]


def test_upload_and_chat_lifecycle():
    """
    Test complete lifecycle:
    1. Upload valid PDF
    2. Retrieve document details & summary
    3. Ask questions about content and verify citations
    4. Verify history persistence in SQLite
    5. Clean up session
    """
    pdf_bytes = generate_sample_pdf_bytes()
    
    # 1. Upload PDF
    upload_res = client.post(
        "/api/upload",
        files={"file": ("sample_report.pdf", pdf_bytes, "application/pdf")}
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    upload_data = upload_res.json()
    assert upload_data["success"] is True
    assert upload_data["page_count"] == 2
    doc_id = upload_data["doc_id"]
    session_id = upload_data["session_id"]
    assert doc_id.startswith("doc_")
    assert session_id.startswith("sess_")
    assert upload_data["filename"] == "sample_report.pdf"
    assert len(upload_data["summary"]) > 0

    # 2. List documents
    docs_res = client.get("/api/documents")
    assert docs_res.status_code == 200
    docs = docs_res.json()["documents"]
    assert any(d["doc_id"] == doc_id for d in docs)

    # 3. Document details & summary
    doc_details_res = client.get(f"/api/documents/{doc_id}")
    assert doc_details_res.status_code == 200
    assert doc_details_res.json()["page_count"] == 2

    summary_res = client.get(f"/api/summary/{doc_id}")
    assert summary_res.status_code == 200
    assert "summary" in summary_res.json()

    # 4. Ask a question targeting Page 1 content
    chat_res_1 = client.post(
        "/api/chat",
        json={
            "doc_id": doc_id,
            "session_id": session_id,
            "message": "What architecture achieved state of the art results in NLP?"
        }
    )
    assert chat_res_1.status_code == 200, f"Chat failed: {chat_res_1.text}"
    chat_data_1 = chat_res_1.json()
    assert "answer" in chat_data_1
    assert len(chat_data_1["answer"]) > 0
    assert len(chat_data_1["citations"]) > 0
    # Page 1 contains the transformer note
    citation_pages_1 = [c["page"] for c in chat_data_1["citations"]]
    assert 1 in citation_pages_1

    # 5. Ask a question targeting Page 2 content
    chat_res_2 = client.post(
        "/api/chat",
        json={
            "doc_id": doc_id,
            "session_id": session_id,
            "message": "What does RAG combine according to the report?"
        }
    )
    assert chat_res_2.status_code == 200
    chat_data_2 = chat_res_2.json()
    citation_pages_2 = [c["page"] for c in chat_data_2["citations"]]
    assert 2 in citation_pages_2

    # 6. Verify conversation history retrieval from SQLite
    hist_res = client.get(f"/api/history/{session_id}")
    assert hist_res.status_code == 200
    messages = hist_res.json()["messages"]
    # 2 user messages + 2 assistant messages = 4 messages
    assert len(messages) == 4
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[3]["role"] == "assistant"

    # 7. Create a new session for the same document
    new_sess_res = client.post(
        "/api/sessions",
        json={"doc_id": doc_id, "title": "Secondary Research Session"}
    )
    assert new_sess_res.status_code == 200
    new_sess_id = new_sess_res.json()["session_id"]
    assert new_sess_id != session_id

    # 8. Delete the secondary session
    del_res = client.delete(f"/api/sessions/{new_sess_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


if __name__ == "__main__":
    pytest.main(["-v", __file__])
