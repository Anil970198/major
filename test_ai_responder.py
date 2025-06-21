# test_ai_responder.py

from core.ai_responder import draft_reply

def test_draft_reply():
    summary = "A vendor is requesting a meeting to showcase their new product. They are available next Wednesday or Thursday."
    drafted_response = draft_reply(summary)
    print("Generated Draft Email:\n")
    print(drafted_response)

if __name__ == "__main__":
    test_draft_reply()
