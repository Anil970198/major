import random
from core.email_service import send_email, load_settings, ollama_client

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

**Final Answer (Only "email", "notify", or "no"):**
"""

# Expanded sample emails
email_samples = [
    "Subject: Meeting Request\n\nHi, can we schedule a quick sync this week about the Q2 roadmap?",
    "Subject: Results Out\n\nYour recent blood test results are now available in the portal.",
    "Subject: SPAM OFFER\n\nCongratulations! You’ve won an iPhone 15 Pro Max. Click here to claim!",
    "Subject: Event Alert\n\nDon't forget the webinar on medical data privacy this Friday!",
    "Subject: Client Feedback Needed\n\nPlease review the attached proposal and share your thoughts.",
    "Subject: Internship Confirmation\n\nWe are pleased to confirm your internship starting June 1st.",
    "Subject: Invoice Payment Reminder\n\nYour invoice #1234 is overdue. Please make payment at the earliest.",
    "Subject: Social Invite\n\nJoin us for a weekend BBQ at my place! RSVP soon.",
    "Subject: Password Reset Request\n\nClick this link to reset your account password.",
    "Subject: New Course Available\n\nCheck out our new online course on Data Science starting next month.",
    "Subject: Alert: Unusual Login Attempt\n\nWe detected a login attempt from a new device.",
    "Subject: Newsletter October\n\nHere’s what’s new this month at our company.",
    "Subject: Confirm Your Email Address\n\nClick here to confirm your email address and activate your account.",
    "Subject: Your Subscription Expires Soon\n\nRenew now to continue enjoying premium features.",
    "Subject: Weekly Update\n\nHere’s your summary of activities from the past week.",
    "Subject: Cancellation Notice\n\nYour scheduled appointment for tomorrow has been canceled.",
    "Subject: Refund Processed\n\nWe’ve issued a refund for your recent purchase.",
    "Subject: New Policy Update\n\nPlease review the updated privacy policy effective from November 1st.",
    "Subject: Action Required: Verify Documents\n\nPlease upload your ID proof to complete verification.",
    "Subject: Welcome Aboard!\n\nWe’re excited to have you join our team starting Monday."
]

# Random shuffle to simulate arrival order
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

def main():
    settings = load_settings()
    monitored_email = settings.get("monitored_email")
    if not monitored_email:
        print("⚠️ No monitored_email set in settings.json.")
        return

    total_sent = 0
    for i, email_body in enumerate(email_samples):
        classification = classify_email(email_body)
        print(f"[Email {i+1}] Classification: {classification}")

        if classification != "no":
            subject_line = email_body.split("\n")[0].replace("Subject:", "").strip()
            message_text = f"{email_body}\n\n[Classified as: {classification}]"
            success, message = send_email(monitored_email, subject_line, message_text)
            print(message)
            if success:
                total_sent += 1
        else:
            print("🛑 Skipping this email (classified as 'no').")

    print(f"\n✅ Summary: {total_sent} emails sent out of {len(email_samples)}.")

if __name__ == "__main__":
    main()
