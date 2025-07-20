# core/ai_responder.py

"""Module to draft a suggested email reply using Groq and LLaMA 3.1."""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables from .env
load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.1-8b-instant"  # ✅ UPDATED model name

# Prompt Template
DRAFT_PROMPT = """
You are a professional executive assistant working for {full_name}, tasked with replying to summarized emails in a clear, concise, and polished manner.

Your job is to draft a response that:
- Maintains a professional and courteous tone.
- Addresses the sender by name or role if available.
- Clearly acknowledges the context or request.
- Responds to questions or proposals appropriately.
- Uses natural, human-sounding phrasing — avoid sounding robotic or too formal unless clearly required.
- Keeps the message short and to the point (4–6 sentences max).

Formatting guidelines:
- Use full sentences and proper grammar.
- Start with a greeting and end with an appropriate closing (e.g., “Best regards, Anil”).
- Avoid redundant statements or vague responses.

Context:
You are responding based solely on a summarized version of the email (not the full thread).

---

Summarized Email:
{summary}

---

Please draft a full reply that {full_name} can send as-is.
"""


def draft_reply(summary: str, full_name: str = "Anil Kumar") -> str:
    """Generates a draft email reply given a summary."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable is not set.")

    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=MODEL_NAME,
        temperature=0.3,
    )

    prompt = DRAFT_PROMPT.format(full_name=full_name)

    # Call Groq model
    response = llm.invoke(prompt)

    return response.content.strip()


# Quick manual test if running this file directly
if __name__ == "__main__":
    sample_summary = "The client is asking if you're available for a project kickoff meeting next Monday afternoon."
    reply = draft_reply(sample_summary)
    print("Suggested Draft:\n", reply)
