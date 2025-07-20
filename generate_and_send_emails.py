import random
from core.email_service import send_email, load_settings, ollama_client
from core.database import session_scope, upsert_email
from datetime import datetime, timezone

TRIAGE_PROMPT_TEMPLATE = """You are an AI email classifier.
You must categorize each email into one of three categories:
- **"no"** → Ignore these emails.
- **"email"** → These require a response.
- **"notify"** → User needs to be notified.

**RULES:**
- **Only return one word:** "email", "notify", or "no".
- **Do NOT explain.**
- **Do NOT return any other words.**
- **If unsure, return "notify" (DO NOT GUESS).**

**Email Content:**
{email_content}

**Final Answer (Only "email", "notify", or "no"):**
"""

# Expanded sample emails to cover all classification cases
email_samples = [
    "Subject: Meeting Request\n\nHi, can we schedule a quick sync this week about the Q2 roadmap?",
    "Subject: Results Out\n\nYour recent blood test results are now available in the portal.",
    "Subject: SPAM OFFER\n\nCongratulations! You’ve won an iPhone 15 Pro Max. Click here to claim!",
    "Subject: Event Alert\n\nDon't forget the webinar on medical data privacy this Friday!",
    "Subject: Client Feedback Needed\n\nPlease review the attached proposal and share your thoughts.",
    "Subject: Invoice Payment Reminder\n\nYour invoice #1234 is overdue. Please make payment at the earliest.",
    "Subject: Alert: Unusual Login Attempt\n\nWe detected a login attempt from a new device.",
    "Subject: Cancellation Notice\n\nYour scheduled appointment for tomorrow has been canceled.",
    "Subject: Action Required: Verify Documents\n\nPlease upload your ID proof to complete verification.",
    "Subject: Welcome Aboard!\n\nWe’re excited to have you join our team starting Monday.",
    "Subject: Weekly Update\n\nHere’s your summary of activities from the past week.",
    "Subject: Feedback on Proposal\n\nPlease revise the attached document and send your feedback.",
    "Subject: Quote Request\n\nCan you provide a quote for the following list of services?",
    "Subject: Support Needed\n\nI'm having trouble accessing my dashboard. Can you help?",
    "Subject: Complaint\n\nThe delivery was delayed and the item was damaged.",
    "Subject: Google Calendar Invite\n\nYou have been invited to a meeting on June 7th at 3 PM.",
    "Subject: Schedule Request\n\nCan we block time for a quick check-in sometime tomorrow?",
    "Subject: Unsubscribe\n\nPlease remove me from your mailing list.",
    "Subject: Verify Account\n\nPlease verify your account to continue using our service.",
    "Subject: Promotion\n\nCheck out our latest deals and offers for this summer!",
    "Subject: Refund Confirmation\n\nYour refund of $120 has been successfully processed.",
    "Subject: Policy Update\n\nPlease review our updated Terms of Service effective next week.",
    "Subject: Reminder: Project Deadline\n\nThis is a reminder that your final report is due by Friday, June 10th at 5PM."
]

random.shuffle(email_samples)


def classify_email(email_body: str) -> str:
    prompt = TRIAGE_PROMPT_TEMPLATE.format(email_content=email_body)
    try:
        response = ollama_client.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt}]
        )
        label = response["message"]["content"].strip().lower()
        if label not in ["email", "notify", "no"]:
            return "notify"
        return label
    except Exception as e:
        print(f"❌ Classification error: {e}")
        return "notify"


def simulate_emails():
    settings = load_settings()
    monitored_email = settings.get("monitored_email")
    if not monitored_email:
        print("⚠️ No monitored_email set in settings.json.")
        return

    total_classified = 0
    total_sent = 0

    for i, email_body in enumerate(email_samples):
        classification = classify_email(email_body)
        print(f"\n[Email {i+1}] Classification: {classification.upper()}")

        subject = email_body.split("\n")[0].replace("Subject:", "").strip()
        snippet = email_body[:150]

        email_data = {
            "gmail_id": f"mock-{i+1}-{random.randint(1000,9999)}",
            "from_addr": "test@example.com",
            "to_addr": monitored_email,
            "subject": subject,
            "snippet": snippet,
            "body": email_body,
            "timestamp": datetime.now(timezone.utc),
            "triage_label": classification
        }

        upsert_email(email_data)
        total_classified += 1

        if classification != "no":
            message_text = f"{email_body}\n\n[Classified as: {classification}]"
            success, message = send_email(monitored_email, subject, message_text)
            print(message)
            if success:
                total_sent += 1
        else:
            print("🛑 Skipping send (classified as 'no').")

    print(f"\n✅ Summary: {total_classified} emails processed, {total_sent} sent.")


if __name__ == "__main__":
    simulate_emails()
