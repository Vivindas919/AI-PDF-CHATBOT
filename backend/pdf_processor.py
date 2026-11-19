"""
PDF Processor module for AI PDF Chatbot.
Extracts page-by-page text, performs chunking with page attribution,
and handles context retrieval for question answering.
"""

import os
import re
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader


def extract_text_from_pdf(file_path: str) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Extracts text from each page of a PDF file.
    Returns:
        total_pages (int): Total number of pages.
        pages (List[Dict]): List of dicts with 'page_number' (1-indexed) and 'content'.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found at {file_path}")

    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    extracted_pages = []

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        try:
            text = page.extract_text() or ""
            # Clean up whitespace and non-printable characters
            clean_text = re.sub(r"[ \t]+", " ", text).strip()
        except Exception as e:
            clean_text = f"[Text extraction error on page {page_num}: {str(e)}]"

        extracted_pages.append({
            "page_number": page_num,
            "content": clean_text
        })

    return total_pages, extracted_pages


def chunk_document_pages(
    pages: List[Dict[str, Any]],
    chunk_size: int = 600,
    chunk_overlap: int = 100
) -> List[Dict[str, Any]]:
    """
    Splits page content into smaller overlapping chunks while preserving page numbers.
    Each chunk retains its source page number for precise citations.
    """
    chunks = []
    chunk_id = 1

    for page in pages:
        page_num = page["page_number"]
        text = page["content"]
        if not text.strip():
            continue

        words = text.split()
        if not words:
            continue

        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append({
                "chunk_id": chunk_id,
                "page_number": page_num,
                "text": chunk_text
            })
            chunk_id += 1
            if end == len(words):
                break
            start += chunk_size - chunk_overlap

    return chunks


def retrieve_relevant_chunks(
    pages: List[Dict[str, Any]],
    query: str,
    top_k: int = 4
) -> List[Dict[str, Any]]:
    """
    Performs keyword & token-overlap retrieval to find the most relevant chunks/pages for a query.
    Used for local RAG retrieval and citation grounding.
    """
    chunks = chunk_document_pages(pages)
    if not chunks:
        return []

    # Clean query into keywords
    stop_words = {
        "what", "is", "the", "a", "an", "and", "or", "in", "of", "to", "for", "on", "with",
        "at", "by", "from", "up", "about", "into", "over", "after", "how", "why", "when",
        "where", "who", "which", "can", "could", "would", "should", "do", "does", "did",
        "this", "that", "these", "those", "are", "was", "were", "been", "has", "have", "had"
    }
    query_tokens = [
        w.lower() for w in re.findall(r"\w+", query)
        if len(w) > 2 and w.lower() not in stop_words
    ]

    if not query_tokens:
        query_tokens = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 1]

    scored_chunks = []
    for chunk in chunks:
        text_lower = chunk["text"].lower()
        chunk_words = re.findall(r"\w+", text_lower)
        chunk_word_set = set(chunk_words)

        score = 0
        matched_terms = []
        for token in query_tokens:
            if token in chunk_word_set:
                count = text_lower.count(token)
                score += (2 + min(count, 5))
                matched_terms.append(token)
            elif any(token in word for word in chunk_word_set):
                score += 1

        # Reward exact phrase matches
        if query.lower() in text_lower:
            score += 10

        scored_chunks.append({
            "chunk_id": chunk["chunk_id"],
            "page_number": chunk["page_number"],
            "text": chunk["text"],
            "score": score,
            "matched_terms": matched_terms
        })

    # Sort descending by score
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)

    # If nothing matched with a score > 0, return the first few chunks (e.g. beginning of document)
    top_results = [c for c in scored_chunks if c["score"] > 0][:top_k]
    if not top_results:
        top_results = scored_chunks[:min(top_k, len(scored_chunks))]

    return top_results

