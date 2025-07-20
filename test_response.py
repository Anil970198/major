import os
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

SECRETS_FILE = "./.secrets/client_secret.json"
TOKEN_FILE = "./.secrets/token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
SENDER = "mondruanilkumar596@gmail.com"
RECIPIENT = "mondruanilkumar596@gmail.com"
SUBJECT_PREFIX = "🧠 Action Required:"

email_bodies = [
    "Hi, I came across your AI assistant. Could you share pricing details and included features?",
    "We are planning to deploy an AI-based support system. Can you send over a quotation?",
    "I'm facing a 403 error while accessing the platform. Can someone assist?",
    "I like the assistant, but can you add an option to adjust reply tone to friendly?",
    "Can we schedule a call next week to walk through the integration steps?",
    "A few of our replies were not sent. Can you check if there's a config issue?",
    "We’re interested in a demo of your product for our internal teams. What slots are available?",
    "The Gmail authentication in your onboarding docs could use more clarity. I got stuck.",
    "Would you be open to discussing a partnership opportunity with our firm?",
    "I created reminders but can’t find where they are stored. Is there a dashboard or view?"
]

def create_message(sender, to, subject, body_text):
    message = MIMEText(body_text)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}

def get_credentials():
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds

def send_test_emails():
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    for i, body in enumerate(email_bodies, start=1):
        subject = f"{SUBJECT_PREFIX} #{i}"
        message = create_message(SENDER, RECIPIENT, subject, body)
        try:
            service.users().messages().send(userId="me", body=message).execute()
            print(f"✅ Sent email #{i}")
        except Exception as e:
            print(f"❌ Failed to send email #{i}: {e}")

send_test_emails()
