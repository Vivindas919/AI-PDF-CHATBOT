"""
Database module for AI PDF Chatbot.
Manages SQLite database storage for documents, extracted pages, chat sessions, and messages.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "chatbot.db")


def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes the database schema if tables do not exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Documents table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                page_count INTEGER NOT NULL,
                upload_date TEXT NOT NULL,
                summary TEXT
            )
            """
        )
        
        # Document pages table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS document_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
            """
        )
        
        # Chat sessions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                doc_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
            """
        )
        
        # Chat messages table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                citations TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
            """
        )
        
        conn.commit()


def save_document(
    doc_id: str,
    filename: str,
    file_path: str,
    page_count: int,
    pages_data: List[Dict[str, Any]],
    summary: Optional[str] = None
) -> None:
    """Saves document metadata and extracted text per page."""
    upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO documents (doc_id, filename, file_path, page_count, upload_date, summary)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (doc_id, filename, file_path, page_count, upload_date, summary)
        )
        
        for p in pages_data:
            cursor.execute(
                """
                INSERT INTO document_pages (doc_id, page_number, content)
                VALUES (?, ?, ?)
                """,
                (doc_id, p["page_number"], p["content"])
            )
            
        conn.commit()


def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves document metadata by doc_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_documents() -> List[Dict[str, Any]]:
    """Retrieves all registered documents ordered by upload date newest first."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_document_pages(doc_id: str) -> List[Dict[str, Any]]:
    """Retrieves extracted text for all pages of a document."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT page_number, content FROM document_pages WHERE doc_id = ? ORDER BY page_number ASC",
            (doc_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def update_document_summary(doc_id: str, summary: str) -> None:
    """Updates the generated summary for a document."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE documents SET summary = ? WHERE doc_id = ?", (summary, doc_id))
        conn.commit()


def create_session(session_id: str, doc_id: str, title: str = "New Chat") -> Dict[str, Any]:
    """Creates a new chat session."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO sessions (session_id, doc_id, title, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, doc_id, title, created_at)
        )
        conn.commit()
    return {"session_id": session_id, "doc_id": doc_id, "title": title, "created_at": created_at}


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a session by session_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_sessions() -> List[Dict[str, Any]]:
    """Retrieves all chat sessions ordered by created_at newest first."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.*, d.filename 
            FROM sessions s
            LEFT JOIN documents d ON s.doc_id = d.doc_id
            ORDER BY s.id DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_session(session_id: str) -> bool:
    """Deletes a session and associated messages."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        return cursor.rowcount > 0


def save_message(
    session_id: str,
    role: str,
    content: str,
    citations: Optional[List[Dict[str, Any]]] = None
) -> int:
    """Saves a message to the session."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    citations_json = json.dumps(citations or [])
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (session_id, role, content, citations, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, role, content, citations_json, timestamp)
        )
        conn.commit()
        return cursor.lastrowid


def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    """Retrieves all messages for a session in chronological order."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, session_id, role, content, citations, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,)
        )
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("citations"):
                try:
                    d["citations"] = json.loads(d["citations"])
                except Exception:
                    d["citations"] = []
            else:
                d["citations"] = []
            result.append(d)
        return result
