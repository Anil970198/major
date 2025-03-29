"""Authenticate and store credentials for Gmail API."""
from core.email_service import get_credentials

if __name__ == "__main__":
    get_credentials()
    print("✅ Gmail API authentication complete!")
