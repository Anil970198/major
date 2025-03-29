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

# 🔧 Constants for storage
SECRETS_DIR = os.path.join(os.path.dirname(__file__), "../.secrets")
SECRETS_FILE = os.path.join(SECRETS_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(SECRETS_DIR, "token.json")
SETTINGS_FILE = os.path.join(SECRETS_DIR, "settings.json")

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# 🔧 Ollama client config
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
ollama_client = ollama.Client(host=OLLAMA_BASE_URL)

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
    You are an AI email assistant that summarizes emails into clear, structured points.
    - Extract key details.
    - Ignore styling, CSS, and ads.
    - Preserve essential links.
    - Convert tables/lists into bullet points.

    Email Content:
    {html_content}

    Provide a structured summary in bullet points:
    """

    try:
        response = ollama_client.chat(model="mistral", messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"].strip()
    except Exception as e:
        print(f"❌ Mistral Summarization Error: {e}")
        return "Error summarizing email content."

def classify_email_with_llama3(summarized_content):
    settings = load_settings()

    triage_no = settings.get("triage_no", [])
    triage_email = settings.get("triage_email", [])
    triage_notify = settings.get("triage_notify", [])

    if not summarized_content:
        return "unknown"

    prompt = f"""
    You are an AI email assistant that classifies emails based on their content.
    - **"no"** → Spam, Promotions, Social Media (triage_no)
    - **"email"** → Client requests, Meeting invites, Schedule requests (triage_email)
    - **"notify"** → Results, Upcoming events, Alerts (triage_notify)

    Use ONLY the labels: "no", "email", or "notify".

    Email Summary:
    {summarized_content}

    Output ONLY the classification label:
    """

    try:
        response = ollama_client.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])
        classification = response["message"]["content"].strip().lower()
        return classification if classification in ["no", "email", "notify"] else "email"
    except Exception as e:
        print(f"❌ LLaMA Classification Error: {e}")
        return "email"

def fetch_emails():
    creds = get_credentials()
    service = get_gmail_service()
    settings = load_settings()
    monitored_email = settings.get("monitored_email", "")
    if not monitored_email:
        return []

    try:
        results = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=5).execute()
        messages = results.get("messages", [])

        email_list = []
        for msg in messages:
            msg_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
            headers = msg_data.get("payload", {}).get("headers", [])

            from_field = next((h["value"] for h in headers if h["name"].lower() in ["from", "reply-to", "sender"]),
                              "Unknown Sender")
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

            # 🔥 Summarize + classify
            summarized_content = summarize_email_content(html_body)
            classification = classify_email_with_llama3(summarized_content)

            email_list.append({
                "from_email": sender,
                "subject": subject,
                "classification": classification,
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
