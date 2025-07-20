import os
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SECRETS_FILE = "./.secrets/client_secret.json"  # or wherever your client_secret.json is
TOKEN_FILE = "./.secrets/token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Load Gmail credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

def get_credentials():
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds

creds = get_credentials()

service = build("gmail", "v1", credentials=creds)

# MANUAL CONFIGURATION
SENDER = "mondruanilkumar596@gmail.com"     # 🔁 Authenticated sender email
RECIPIENT = "mondruanilkumar596@gmail.com"  # 🔁 Receiver (monitored email in your app)

# Email messages
messages = [
    "Please submit the report by June 10, 5 PM.",
    "Kindly upload your assignment before June 11, 3 PM.",
    "Finish the project draft by June 12th end of day.",
    "Send the invoice by June 13 at 11 AM.",
    "Submit your application before June 14, 6 PM.",
    "Finalize the design files by June 15, 10 AM.",
    "Schedule your meeting by June 16, 2 PM.",
    "Upload the documentation by June 17 EOD.",
    "Confirm attendance by June 18 morning.",
    "Complete the checklist by June 19, 5 PM."
]

def create_message(sender, to, subject, body_text):
    message = MIMEText(body_text)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}

# Send the emails
for i, body in enumerate(messages, start=1):
    subject = f"🔔 Task #{i} Reminder: Deadline Approaching"
    msg = create_message(SENDER, RECIPIENT, subject, body)
    try:
        service.users().messages().send(userId="me", body=msg).execute()
        print(f"✅ Sent: {subject}")
    except Exception as e:
        print(f"❌ Failed to send: {e}")
