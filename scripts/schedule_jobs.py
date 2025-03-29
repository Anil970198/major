"""Set up a cron job that runs every 10 minutes to check for emails."""
import argparse
import asyncio
import httpx  # Added to check API health
from typing import Optional
from langgraph_sdk import get_client


async def is_server_running(url: str) -> bool:
    """Checks if the LangGraph API server is running."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url + "/health")  # Checking server health
            return response.status_code == 200
    except Exception:
        return False


async def main(url: Optional[str] = None, minutes_since: int = 60):
    """Creates a cron job to fetch emails every 10 minutes."""
    api_url = url or "http://127.0.0.1:2024"

    # Check if LangGraph server is running
    if not await is_server_running(api_url):
        print(f"❌ Error: LangGraph server is not running at {api_url}.")
        print("➡ Start the server using: `langgraph up --port 2024`")
        return

    # Initialize client
    client = get_client(url=api_url)

    # Schedule the cron job
    try:
        response = await client.crons.create(
            "workflow_manager",  # ✅ Ensure this matches your LangGraph workflow name
            schedule="*/10 * * * *",  # Runs every 10 minutes
            input={"minutes_since": minutes_since}
        )
        print(f"✅ Cron job scheduled successfully! Runs every 10 minutes.")
    except Exception as e:
        print(f"❌ Failed to schedule cron job: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up automated email fetching every 10 minutes.")
    parser.add_argument("--url", type=str, default=None, help="API URL to use for scheduling the job.")
    parser.add_argument("--minutes-since", type=int, default=60, help="Only process emails newer than this time.")

    args = parser.parse_args()
    asyncio.run(main(url=args.url, minutes_since=args.minutes_since))
