import os
import json
import base64
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import ollama  # Local LLM models (Mistral for summarization, LLaMA for classification)
from langchain_groq import ChatGroq

# 🔧 Constants for storage
SECRETS_DIR = os.path.join(os.path.dirname(__file__), "../.secrets")
SECRETS_FILE = os.path.join(SECRETS_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(SECRETS_DIR, "token.json")
SETTINGS_FILE = os.path.join(SECRETS_DIR, "settings.json")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]

# 🔧 Ollama client config
summarizer_llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile",  # 🧠 High-context summarizer
    temperature=0.3,
    max_tokens=32768
)


classifier_llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name=os.getenv("CLASSIFIER_MODEL", "llama-3.1-8b-instant")
)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as file:
            return json.load(file)
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as file:
        json.dump(settings, file, indent=4)

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds

def get_gmail_service():
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def set_monitored_email(email):
    settings = load_settings()
    old_email = settings.get("monitored_email", "")
    if old_email != email:
        settings["monitored_email"] = email
        save_settings(settings)
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        get_credentials()

def extract_email_address(from_field):
    match = re.search(r'<(.+?)>', from_field)
    return match.group(1) if match else from_field.strip()

def summarize_email_content(html_content):
    if not html_content:
        return "No content available."

    prompt = f"""
    You are an AI email assistant.

    📌 Your job is to **summarize the ENTIRE email content** into clear, structured, and useful bullet points for the user.

    🔒 HARD LIMITS:
    - The summary must fit **within 32,768 tokens maximum.**
    - Be concise but do not skip important content.
    - The full email content must be **made understandable** within this limit.
    - Do NOT allow cutoffs. Ensure it feels complete.

    📋 Guidelines:
    - Highlight main points, requests, links, meeting details, deadlines, or questions.
    - Ignore CSS, headers, footers, legal disclaimers, and promotional content.
    - Preserve structure (bullets, numbered points, section headers).
    - Group similar content together.
    - Minimum 5, ideally 7–10 distinct bullet points.

    Email Content:
    {html_content}

    ---

    Return only the summary as clean, readable bullet points.
    """
    try:
        response = summarizer_llm.invoke([{"role": "user", "content": prompt}])
        return response.content.strip()
    except Exception as e:
        print(f"❌ Mistral Summarization Error: {e}")
        return "Error summarizing email content."


def classify_email_with_llama3(summarized_content):
    if not summarized_content:
        return {"label": "notify", "subtype": "UPCOMING_EVENT"}

    prompt = f"""
You are a highly accurate AI email triage assistant. Your job is to:

1. Determine if the email requires a reply, is just a notification, or should be ignored.
2. Pick the appropriate subtype from a fixed list.
3. Detect any clear deadlines, due dates, or times — and return them in ISO format if found.
4. Respond ONLY in valid JSON.

---

Your response must strictly follow this format:
{{
  "label": "email" | "notify" | "no",
  "subtype": "<see subtype options>",
  "due_time": "YYYY-MM-DDTHH:MM:SSZ"  // only if a clear deadline is found
}}

---

Subtype values:
email:
- INFO_REQUEST
- QUOTE_PROPOSAL
- SUPPORT_ISSUE
- FEEDBACK_COMPLAINT
- MEETING_INVITE
- SCHEDULE_REQUEST
- DEADLINE_TASK

notify:
- RESULT
- UPCOMING_EVENT
- ALERT

no:
- SPAM
- PROMOTION
- SOCIAL

---

Summarized Email:
\"\"\"
{summarized_content}
\"\"\"

Final JSON:
"""

    try:
        response = classifier_llm.invoke([{"role": "user", "content": prompt}])
        raw = response.content.strip()

        match = re.search(r"\{.*?\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return {
                "label": data.get("label", "notify").lower(),
                "subtype": data.get("subtype", "UPCOMING_EVENT").upper(),
                "due_time": data.get("due_time")
            }
        else:
            return {"label": "notify", "subtype": "UPCOMING_EVENT", "due_time": None}

    except Exception as e:
        print(f"❌ LLaMA Classification Error: {e}")
        return {"label": "notify", "subtype": "UPCOMING_EVENT", "due_time": None}



from core.database import Email, session_scope  # 🔥 Import at the top of the file

from core.database import Email, session_scope  # already imported

def fetch_emails():
    creds = get_credentials()
    service = get_gmail_service()
    settings = load_settings()
    monitored_email = settings.get("monitored_email", "")
    if not monitored_email:
        return []

    try:
        results = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=20).execute()
        messages = results.get("messages", [])

        email_list = []
        for msg in messages:
            msg_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
            headers = msg_data.get("payload", {}).get("headers", [])

            from_field = next((h["value"] for h in headers if h["name"].lower() in ["from", "reply-to", "sender"]), "Unknown Sender")
            sender = extract_email_address(from_field)
            subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")

            payload = msg_data.get("payload", {})
            text_body = ""
            html_body = ""

            if "parts" in payload:
                for part in payload["parts"]:
                    mime_type = part.get("mimeType", "")
                    data = part.get("body", {}).get("data", "")
                    if data:
                        decoded_data = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        if mime_type == "text/plain":
                            text_body = decoded_data.strip()
                        elif mime_type == "text/html":
                            html_body = decoded_data.strip()
            elif "body" in payload and "data" in payload["body"]:
                text_body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")

            if not html_body and text_body:
                html_body = f"<p>{text_body}</p>"

            summarized_content = summarize_email_content(html_body)
            triage_data = classify_email_with_llama3(summarized_content)
            label = triage_data["label"]
            subtype = triage_data["subtype"]

            # ✅ INSERT INTO DATABASE (skip if already exists)
            with session_scope() as db:
                exists = db.query(Email).filter_by(gmail_id=msg["id"]).first()
                if not exists:
                    email_record = Email(
                        gmail_id=msg["id"],
                        from_addr=sender,
                        to_addr=monitored_email,
                        subject=subject,
                        snippet=summarized_content[:150],
                        body=html_body,
                        triage_label=label,
                        triage_subtype=subtype,
                        draft_reply=json.dumps({"due_time": triage_data.get("due_time")}) if triage_data.get(
                            "due_time") else None
                    )

                    db.add(email_record)
                    print(f"✅ Inserted email '{subject}'")
                else:
                    print(f"⚠️ Email '{subject}' already in DB → skipping")

            email_list.append({
                "from_email": sender,
                "subject": subject,
                "classification": label,
                "subtype": subtype,
                "summary": summarized_content,
                "html_content": html_body,
            })

        return email_list

    except Exception as e:
        print(f"❌ Error fetching emails: {e}")
        return []


def send_email(to_email, subject, message_text):
    service = get_gmail_service()
    settings = load_settings()
    monitored_email = settings.get("monitored_email")

    if not monitored_email:
        return False, "No monitored email set."

    if not to_email or not subject or not message_text:
        return False, "Missing required fields."

    try:
        message = MIMEText(message_text)
        message["to"] = to_email
        message["from"] = monitored_email
        message["subject"] = subject

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message_body = {"raw": raw_message}

        service.users().messages().send(userId="me", body=message_body).execute()
        return True, f"✅ Email sent to {to_email}!"
    except Exception as e:
        return False, f"❌ Error sending email: {e}"
