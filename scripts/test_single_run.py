# scripts/test_run.py

from core.email_service import fetch_emails


def main():
    print("\n📨 Fetching and classifying emails...\n")
    emails = fetch_emails()

    if not emails:
        print("⚠ No emails found or something went wrong.")
        return

    for idx, email in enumerate(emails, start=1):
        print(f"\n📧 Email #{idx}")
        print(f"From       : {email['from_email']}")
        print(f"Subject    : {email['subject']}")
        print(f"Classified : {email['classification']}")
        print(f"Summary    :\n{email['summary']}")
        print("-" * 50)


if __name__ == "__main__":
    main()
