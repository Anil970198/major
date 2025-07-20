import os
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SECRETS_FILE = "./.secrets/client_secret.json"
TOKEN_FILE = "./.secrets/token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def get_credentials():
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not creds.valid and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds

creds = get_credentials()
service = build("gmail", "v1", credentials=creds)

# ✅ Same sender & recipient to trigger deduplication logic
SENDER = "mondruanilkumar596@gmail.com"
RECIPIENT = "mondruanilkumar596@gmail.com"

# ✅ Meeting-style emails
meeting_emails = [
    "Hi, can we schedule a meeting to discuss the Q2 report next week?",
    "Let's fix a time to go over the project updates. I'm free Wednesday 3 PM.",
    "Are you available Friday morning for a quick sync?",
    "I'd like to schedule a call regarding the design review. How about Thursday?",
    "Can we meet next Monday at 10 AM to finalize the requirements?",
    "Please arrange a calendar invite for the monthly team review.",
    "Schedule a discussion to resolve the pending issues before launch.",
    "Let's schedule a brainstorming session next week.",
    "I'd like to block some time this Friday for a deep-dive meeting.",
    "Are we still on for the budget planning meeting next Tuesday?"
]

def create_message(sender, to, subject, body_text):
    message = MIMEText(body_text)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}

# ✅ Send test meeting emails
for i, body in enumerate(meeting_emails, start=1):
    subject = f"📅 Meeting Request #{i}"
    msg = create_message(SENDER, RECIPIENT, subject, body)
    try:
        service.users().messages().send(userId="me", body=msg).execute()
        print(f"✅ Sent: {subject}")
    except Exception as e:
        print(f"❌ Failed to send: {e}")
