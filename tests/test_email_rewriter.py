# tests/test_email_rewriter.py

import asyncio
import sys
import os

# Adjust path if necessary to find core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.email_rewriter import rewrite_email


def run_rewrite_tests():
    draft_email = "Hi John, just checking if you're available for our project sync next week. Let me know!"

    tones_to_test = [
        "formal",
        "casual",
        "assertive",
        "friendly",
        "apologetic",
    ]

    async def inner():
        print("\nOriginal Draft:\n")
        print(draft_email)
        print("\n")

        for tone in tones_to_test:
            print(f"--- Rewriting in tone: {tone} ---")
            rewritten = await rewrite_email(draft_email, tone=tone)
            print(rewritten)
            print("\n")

    asyncio.run(inner())


if __name__ == "__main__":
    run_rewrite_tests()
