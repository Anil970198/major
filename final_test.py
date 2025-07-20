import os
from langchain_groq import ChatGroq
from core.email_service import send_email  # Make sure this works

# Groq API setup
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant"
)

EMAIL_SUBTYPES = {
    "INFO_REQUEST": "The user is asking for more details or clarification.",
    "QUOTE_PROPOSAL": "A company requests pricing or a business proposal.",
    "SUPPORT_ISSUE": "The sender is reporting a bug or requesting technical help.",
    "FEEDBACK_COMPLAINT": "The user is giving feedback or raising a complaint.",
    "MEETING_INVITE": "This email invites someone to a specific meeting or call.",
    "SCHEDULE_REQUEST": "Someone is asking to set or reschedule a meeting.",
    "DEADLINE_TASK": "The sender is assigning or reminding about a task with a due date.",
    "RESULT": "This informs someone about an outcome (like selection or exam).",
    "UPCOMING_EVENT": "This email notifies about an event that’s going to happen.",
    "ALERT": "The message includes a warning or security notice.",
    "SPAM": "Obvious junk or reward email meant to trick the user.",
    "PROMOTION": "Marketing content with offers or discounts.",
    "SOCIAL": "Social media notifications like friend requests or likes."
}

def build_prompt(subtype: str, description: str) -> str:
    return f"""
            You are writing a short, realistic email for testing an AI assistant.

Guidelines:
- The email must clearly reflect the **{subtype}** category.
- Write exactly 2 paragraphs — no longer than 5–7 total lines.
- Do NOT include irrelevant details or mention labels like "this is a quote".
- The tone should be professional or neutral.
- If this is a DEADLINE_TASK, include a real due date like "June 8th, 5PM IST".
- The email should feel natural and plausible but short enough to summarize.

Only write the email content. Do NOT include a subject line or greeting unless it makes sense.

Context:
{description}
""".strip()

TO_EMAIL = os.getenv("TO_EMAIL") or "mondruanilkumar596@gmail.com"

def generate_and_send_emails():
    print("📬 Generating and sending 13 demo-safe emails using LLaMA 3.2 8B...\n")
    for i, (subtype, desc) in enumerate(EMAIL_SUBTYPES.items(), 1):
        prompt = build_prompt(subtype, desc)
        subject = f"Test Email – {subtype.replace('_', ' ').title()}"

        print(f"[{i:02}] Generating → {subtype}")
        try:
            response = llm.invoke(prompt)
            body = response.content.strip().replace("Subject:", "")
            send_email(TO_EMAIL, subject, body.lstrip())
            print("✓ Sent successfully.\n")
        except Exception as e:
            print(f"✗ Failed to send {subtype}: {e}\n")

    print("✅ All demo test emails processed.")

if __name__ == "__main__":
    generate_and_send_emails()
