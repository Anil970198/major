import os
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SECRETS_DIR = os.path.join(os.path.dirname(__file__), ".secrets")
TOKEN_FILE = os.path.join(SECRETS_DIR, "token.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Load Gmail credentials
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
service = build("gmail", "v1", credentials=creds)

# Set your email here
SENDER = "youremail@gmail.com"  # 🔁 replace if needed

# Reminder-worthy messages
test_emails = [
    ("Assignment Reminder", "Please submit your assignment by June 10th."),
    ("Project Deadline", "Your final year project report is due by June 15, 5PM."),
    ("Reminder", "Schedule your internship interview before next Monday."),
    ("Medical Report", "Upload your health records by June 9th midnight."),
    ("Exam Alert", "Prepare for the AI exam — it's scheduled for June 14."),
    ("Scholarship Form", "Fill and submit the scholarship form soon."),
    ("Documentation", "Don’t forget to compile documentation for your internship."),
    ("Team Review", "Project review scheduled early next week — be ready."),
    ("Lab Attendance", "Your lab work should be completed this weekend."),
    ("Workshop", "Join the ML workshop. Starts Friday at 10am.")
]

def create_message(sender, to, subject, body_text):
    message = MIMEText(body_text)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}

# Send emails
for subject, body in test_emails:
    msg = create_message(SENDER, SENDER, subject, body)
    try:
        service.users().messages().send(userId="me", body=msg).execute()
        print(f"✅ Sent: {subject}")
    except Exception as e:
        print(f"❌ Failed to send {subject}: {e}")
