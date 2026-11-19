"""
AI Engine module for AI PDF Chatbot.
Handles LLM question answering with Google Gemini API and
includes an intelligent offline fallback mode for local testing and demos.
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# Attempt importing google.generativeai
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False


def get_api_key(custom_key: Optional[str] = None) -> Optional[str]:
    """Retrieves Gemini API key from parameters, .env, or environment variables."""
    if custom_key and custom_key.strip():
        return custom_key.strip()
    return os.getenv("GEMINI_API_KEY", "").strip() or None


def generate_document_summary(
    pages: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> str:
    """
    Generates a structured executive summary of the document.
    Uses Gemini if an API key is available, else creates an extractive summary.
    """
    if not pages:
        return "The document appears to be empty or contains no readable text."

    # Combine text from first few pages (up to 3000 words)
    combined_sample = []
    total_words = 0
    for p in pages:
        text = p["content"].strip()
        if text:
            words = text.split()
            combined_sample.append(f"[Page {p['page_number']}]\n{text}")
            total_words += len(words)
            if total_words > 2500:
                break

    sample_text = "\n\n".join(combined_sample)
    key = get_api_key(api_key)

    if key and GEMINI_AVAILABLE:
        try:
            genai.configure(api_key=key)
            # Try gemini-1.5-flash or gemini-pro
            model_name = "gemini-1.5-flash"
            try:
                model = genai.GenerativeModel(model_name)
                prompt = (
                    "You are an expert document analyst. Provide a clear, professional summary of the following document.\n"
                    "Structure your response with:\n"
                    "1. Overview (2-3 sentences)\n"
                    "2. Key Topics / Findings (3-5 bullet points)\n"
                    "3. Conclusion / Significance (1-2 sentences)\n\n"
                    f"Document excerpt:\n{sample_text}"
                )
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception:
                # Fallback model
                model = genai.GenerativeModel("gemini-pro")
                response = model.generate_content(f"Summarize this document clearly in 3-5 bullet points:\n\n{sample_text}")
                if response and response.text:
                    return response.text.strip()
        except Exception as e:
            # Fall back to extractive summary if API call fails
            pass

    # Offline / Extractive fallback summary
    first_page_text = pages[0]["content"].strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", first_page_text) if len(s.strip()) > 20]
    lead_summary = " ".join(sentences[:3]) if sentences else "Document uploaded and parsed successfully."

    total_pages = len(pages)
    total_words = sum(len(p["content"].split()) for p in pages)

    return (
        f"**Document Overview:**\n"
        f"- **Total Pages:** {total_pages}\n"
        f"- **Approximate Word Count:** ~{total_words:,} words\n\n"
        f"**Lead Summary Excerpt (Page 1):**\n"
        f"{lead_summary}\n\n"
        f"> *Tip: Provide a `GEMINI_API_KEY` in the sidebar or `.env` for generative deep-dive summaries.*"
    )


def answer_question(
    query: str,
    pages: List[Dict[str, Any]],
    chat_history: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Answers a query using relevant document context with source citations.
    """
    from backend.pdf_processor import retrieve_relevant_chunks

    relevant_chunks = retrieve_relevant_chunks(pages, query, top_k=4)
    if not relevant_chunks:
        return {
            "answer": "I could not find any text in this document related to your question.",
            "citations": [],
            "mode": "offline_fallback"
        }

    # Format citations list
    citations = []
    seen_pages = set()
    for c in relevant_chunks:
        page_num = c["page_number"]
        if page_num not in seen_pages:
            seen_pages.add(page_num)
            snippet = c["text"][:160].replace("\n", " ").strip() + "..."
            citations.append({"page": page_num, "snippet": snippet})

    # Prepare context block
    context_blocks = []
    for c in relevant_chunks:
        context_blocks.append(f"--- [Page {c['page_number']}] ---\n{c['text']}")
    context_str = "\n\n".join(context_blocks)

    key = get_api_key(api_key)

    if key and GEMINI_AVAILABLE:
        try:
            genai.configure(api_key=key)
            prompt = (
                "You are an accurate and helpful AI PDF Assistant.\n"
                "Answer the user's question clearly and concisely based ONLY on the provided document excerpts below.\n"
                "Rules:\n"
                "1. Ground your answer in the provided text.\n"
                "2. Explicitly cite the page number(s) you reference, for example: [Page 2].\n"
                "3. If the answer cannot be determined from the excerpts, state: 'The provided document does not contain enough information to answer this question.'\n\n"
                f"Document Excerpts:\n{context_str}\n\n"
                f"User Question: {query}\n\n"
                "Helpful Answer (with page citations):"
            )

            # Try modern models with fallback
            for model_name in ["gemini-1.5-flash", "gemini-pro"]:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    if response and response.text:
                        return {
                            "answer": response.text.strip(),
                            "citations": citations,
                            "mode": "gemini"
                        }
                except Exception:
                    continue
        except Exception:
            pass

    # Intelligent offline synthesis fallback
    top_chunk = relevant_chunks[0]
    matched_sentences = []
    sentences = re.split(r"(?<=[.!?])\s+", top_chunk["text"])
    query_words = set(re.findall(r"\w+", query.lower()))

    for s in sentences:
        s_words = set(re.findall(r"\w+", s.lower()))
        overlap = query_words.intersection(s_words)
        if len(overlap) >= 2 or (len(overlap) >= 1 and len(query_words) <= 3):
            matched_sentences.append(s.strip())

    if matched_sentences:
        answer_body = " ".join(matched_sentences[:3])
    else:
        answer_body = top_chunk["text"][:350].strip() + "..."

    offline_answer = (
        f"{answer_body}\n\n"
        f"*(Referenced from **Page {top_chunk['page_number']}**)*\n\n"
        f"> *Note: Running in offline semantic retrieval mode. Enter a `GEMINI_API_KEY` in the sidebar for full conversational synthesis.*"
    )

    return {
        "answer": offline_answer,
        "citations": citations,
        "mode": "offline_synthesizer"
    }

