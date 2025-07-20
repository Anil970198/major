# core/email_rewriter.py

import ollama
import asyncio
import os
import logging
from langchain_groq import ChatGroq
from concurrent.futures import ThreadPoolExecutor


# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model Config
MODEL_NAME = os.getenv("REWRITER_MODEL", "mistral-saba-24b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name=MODEL_NAME,
)

def sync_generate(prompt: str) -> str:
    response = llm.invoke([{"role": "user", "content": prompt}])
    return response.content.strip()


async def rewrite_email(draft_text: str, tone: str = "polite and professional") -> str:
    """
    Rewrite the given email draft into the specified tone.

    Args:
        draft_text (str): The original AI-generated draft email.
        tone (str): Desired tone for rewriting (e.g., formal, casual, assertive).

    Returns:
        str: The rewritten email.
    """
    prompt = f"""
    You are an expert email assistant and communication specialist.

    Your task is to rewrite the following email draft to reflect the tone: **"{tone}"**.

    Tone Guidance:
    - **Formal** → Professional, courteous, avoids contractions, respectful phrasing
    - **Casual** → Friendly, relaxed, uses contractions, natural voice
    - **Assertive** → Confident, direct, to-the-point without being rude
    - **Friendly** → Warm, approachable, encouraging language
    - **Apologetic** → Shows empathy, responsibility, and offers solutions

    Instructions:
    - Do NOT change the core message or meaning.
    - Do NOT shorten or expand unnecessarily — preserve overall length and structure.
    - Fix grammar or clarity issues if found.
    - Output ONLY the rewritten version — do not add headers or explanations.

    ---

    Original Email Draft:
    {draft_text}

    ---

    Now rewrite this to reflect the **"{tone}"** tone:
    """

    try:
        logger.info(f"Rewriting email in tone: {tone}")
        loop = asyncio.get_running_loop()
        rewritten_text = await loop.run_in_executor(ThreadPoolExecutor(), sync_generate, prompt)
        return rewritten_text
    except Exception as e:
        logger.error(f"Failed to rewrite email: {e}")
        raise RuntimeError("Email rewriting failed.")

# For manual testing (optional)
if __name__ == "__main__":
    import asyncio

    async def test():
        sample_draft = "Hi John, just checking if you are available for the meeting next week."
        rewritten = await rewrite_email(sample_draft, tone="formal")
        print("Rewritten Email:\n", rewritten)

    asyncio.run(test())
