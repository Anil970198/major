import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

# Load client_secret.json
CLIENT_SECRET_FILE = "/Users/anilkumar/PyCharm Projects/major/.secrets/client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_refresh_token():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    # Print the refresh token
    print("Your refresh token is:", creds.refresh_token)


if __name__ == "__main__":
    get_refresh_token()
