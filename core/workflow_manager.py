import json
from typing import TypedDict, Literal
from langgraph.graph import END, StateGraph
from core.email_service import fetch_emails
from core.email_classifier import classify_email


def process_emails(state):
    """Fetches emails and prepares them for classification."""
    try:
        emails = fetch_emails()
        if not emails:
            print("⚠ No new emails found.")
            return {"emails": []}  # No emails fetched
        return {"emails": emails}
    except Exception as e:
        print(f"❌ Error fetching emails: {e}")
        return {"emails": []}  # Return an empty list on failure


def classify_emails(state):
    """Classifies emails using LLaMA 3.2."""
    classified_emails = []
    for email in state["emails"]:
        summary = email.get("summary", "").strip()
        if not summary:
            print(f"⚠ Skipping email from {email['from_email']} (No summary available)")
            continue  # Skip emails without summaries

        classification = classify_email(summary)
        email["classification"] = classification
        classified_emails.append(email)

    return {"emails": classified_emails}


def log_results(state):
    """Logs final classified emails for debugging or storage."""
    print("✅ Classified Emails:")
    print(json.dumps(state["emails"], indent=4))
    return state  # Return final state in case other scripts need it


class ConfigSchema(TypedDict):
    db_id: int
    model: str


# Define the workflow graph
workflow = StateGraph(dict, config_schema=ConfigSchema)
workflow.add_node("fetch_emails", process_emails)
workflow.add_node("classify_emails", classify_emails)
workflow.add_node("log_results", log_results)

workflow.set_entry_point("fetch_emails")
workflow.add_edge("fetch_emails", "classify_emails")
workflow.add_edge("classify_emails", "log_results")
workflow.add_edge("log_results", END)

# Compile the workflow graph
graph = workflow.compile()
