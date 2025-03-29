import asyncio
from core.email_classifier import triage_input
from core.config_loader import get_config

# Mock email state (Test email for classification)
# state = {
#     "email": {
#         "page_content": "Hello, I would like to schedule a meeting regarding our upcoming project.",
#         "from_email": "client@example.com",
#         "to_email": "user@example.com",
#         "subject": "Meeting Request",
#     },
#     "messages": []
# }

# state = {
#     "email": {
#         "page_content": "Reminder: The annual company meeting is scheduled for next Monday.",
#         "from_email": "admin@company.com",
#         "to_email": "anil@example.com",
#         "subject": "Upcoming Annual Meeting",
#     },
#     "messages": []
# }


state = {
    "email": {
        "page_content": "Congratulations! You've won a free iPhone. Click here to claim your prize.",
        "from_email": "spam@fake.com",
        "to_email": "anil@example.com",
        "subject": "Free iPhone Giveaway!",
    },
    "messages": []
}


# Load config (No OpenAI, Using Ollama)
config = {"configurable": {"model": "llama3"}}  # Ensure model matches what's in settings.yaml
store = None  # Placeholder since we're not using a real store

async def test_triage():
    response = await triage_input(state, config, store)
    print("AI Response:", response)

# Run the test
asyncio.run(test_triage())
