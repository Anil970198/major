import sys
import os
import logging
import ollama
import re
from core.data_models import State

# Ensure the correct module path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔧 Model name and host config
MODEL_NAME = "llama3.2"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

# Strict prompt for classification
TRIAGE_PROMPT_TEMPLATE = """You are an AI email classifier.
You must categorize each email into one of three categories:
- **"no"** → Ignore these emails.
- **"email"** → These require a response.
- **"notify"** → User needs to be notified.

**RULES:**
- **Only return one word:** `"email"`, `"notify"`, or `"no"`.
- **Do NOT explain.**
- **Do NOT return any other words.**
- **If unsure, return `"notify"` (DO NOT GUESS).**

**Email Content:**
{email_content}

**Final Answer (Only "email", "notify", or "no"):**"""

def classify_email(email_body):
    """Sends the classification prompt to Ollama."""
    try:
        if not email_body.strip():
            return "notify"  # Default if no content

        input_prompt = TRIAGE_PROMPT_TEMPLATE.format(email_content=email_body)

        client = ollama.Client(host=OLLAMA_BASE_URL)
        response = client.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": input_prompt}]
        )

        raw_response = response["message"]["content"].strip().lower()

        # ✅ Enforce strict output
        match = re.search(r"\b(email|notify|no)\b", raw_response)
        if match:
            return match.group(1)

        logger.warning(f"Unexpected AI response format: {raw_response}, defaulting to 'notify'")
        return "notify"

    except Exception as e:
        logger.error(f"Error communicating with Ollama: {e}")
        return "error"
