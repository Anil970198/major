import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]  # Scope for reading/sending emails
SECRETS_PATH = "/Users/anilkumar/PyCharm Projects/major/.secrets/client_secret.json"
TOKEN_PATH = "/Users/anilkumar/PyCharm Projects/major/.secrets/token.json"

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(SECRETS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)  # Opens a browser for authentication
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())  # Save token for future use
    return creds


get_credentials()