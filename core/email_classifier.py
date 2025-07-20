import os
import logging
import json
import re
from langchain_groq import ChatGroq

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model & Auth
# MODEL_NAME = os.getenv("CLASSIFIER_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq client
llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name = "mixtral-8x7b-32768"
)

TRIAGE_PROMPT_TEMPLATE = """
You are an advanced executive assistant trained to triage incoming emails with perfect accuracy.

Your responsibilities are:
1. Carefully read the entire email.
2. Decide which of the 3 main categories (label) it belongs to: "email", "notify", or "no".
3. Then assign exactly one subtype from the fixed list.
4. If the email includes a specific due date/time, extract it in ISO 8601 UTC format as "due_time".
5. Output ONLY a valid JSON object. Do NOT include commentary, markdown, or explanations.

---

🔹 LABEL OPTIONS:
- "email" → The sender expects a reply, decision, or action from the recipient.
- "notify" → The email informs the user of something important, but no reply is needed.
- "no" → Spam, marketing, or social notifications that require no attention.

---

🔹 HOW TO THINK ABOUT SUBTYPES:

📦 INFO_REQUEST
Email:
"I'm reviewing our contract, but I’m confused about the clause related to early termination. Could you clarify what penalties apply if we cancel within the first six months?"

How you should interpret this:
The sender is clearly asking for detailed information about a policy. They’re not reporting a problem or making a decision — they’re trying to understand something before acting.

Correct Classification:
→ "label": "email", "subtype": "INFO_REQUEST"

📦 QUOTE_PROPOSAL
Email:
"We’re interested in integrating your analytics dashboard into our platform. Could you send over a proposal including licensing costs and timeline?"

How you should interpret this:
The sender is requesting pricing and service terms. This is a classic pre-sales inquiry where the recipient is expected to respond with a structured offer.

Correct Classification:
→ "label": "email", "subtype": "QUOTE_PROPOSAL"

📦 SUPPORT_ISSUE
Email:
"After the latest update, the dashboard stops loading after login. It just hangs on a white screen. I’ve tried clearing cache and different browsers."

How you should interpret this:
This message reports a malfunction. The sender is describing steps they've already tried, which confirms they’re seeking technical help, not just giving feedback.

Correct Classification:
→ "label": "email", "subtype": "SUPPORT_ISSUE"

📦 FEEDBACK_COMPLAINT
Email:
"I love the new layout — it’s much easier to navigate. However, the load times are slower than before, especially on mobile."

How you should interpret this:
This is mixed feedback. It’s not a support ticket, because no help is being asked for. The sender is simply sharing their experience — both positive and negative.

Correct Classification:
→ "label": "email", "subtype": "FEEDBACK_COMPLAINT"

📦 MEETING_INVITE
Email:
"Would you be available to meet tomorrow at 4PM to go over the new onboarding plan? I’ve sent a Zoom link in case that time works."

How you should interpret this:
The message proposes a specific time and offers a way to connect. It’s a clear invitation — even though it’s phrased as a question, the intent is to schedule a meeting.

Correct Classification:
→ "label": "email", "subtype": "MEETING_INVITE"

📦 SCHEDULE_REQUEST
Email:
"Apologies, but I’ll be unavailable tomorrow. Could we shift our product review meeting to later this week — maybe Friday?"

How you should interpret this:
The sender is not inviting you or assigning a task. They’re requesting a time change, which makes this a scheduling negotiation.

Correct Classification:
→ "label": "email", "subtype": "SCHEDULE_REQUEST"

📦 DEADLINE_TASK
Email:
"Reminder: Please submit the final invoice by June 9th, 5PM IST so we can process payment before the new cycle begins."

How you should interpret this:
This email assigns a task (submitting the invoice) and attaches a strict due date. The user is expected to act by a specific time.

Correct Classification:
→ "label": "email", "subtype": "DEADLINE_TASK"

📦 RESULT
Email:
"Thank you for your application. We’re happy to inform you that you’ve been shortlisted for the next stage. No action is required from your side at this point."

How you should interpret this:
The sender is sharing an outcome — not asking anything. It’s a status update, and clearly doesn’t require a reply.

Correct Classification:
→ "label": "notify", "subtype": "RESULT"

📦 UPCOMING_EVENT
Email:
"Join our DevCon 2025 kickoff on June 15th at 2PM IST. We’ll be announcing some exciting roadmap items. RSVP is optional."

How you should interpret this:
This is an event announcement. No action is required, and the tone is informative. The primary purpose is awareness.

Correct Classification:
→ "label": "notify", "subtype": "UPCOMING_EVENT"

📦 ALERT
Email:
"We detected a login to your account from an unrecognized device in Germany. If this wasn’t you, please review your security settings."

How you should interpret this:
It’s a security notification. It’s not spam, not asking for feedback — it’s informing the user of potential risk.

Correct Classification:
→ "label": "notify", "subtype": "ALERT"

📦 SPAM
Email:
"Dear user, you have been selected to receive $10,000 in cryptocurrency! Claim your reward by clicking the link below before midnight!"

How you should interpret this:
This is clickbait. It’s manipulative, has fake urgency, and is not from a trusted context.

Correct Classification:
→ "label": "no", "subtype": "SPAM"

📦 PROMOTION
Email:
"Summer Sale is here! Get 40% off on all fashion and accessories — only till Sunday. Don’t miss it!"

How you should interpret this:
This is a commercial message. It advertises a discount and doesn’t ask for any feedback or discussion.

Correct Classification:
→ "label": "no", "subtype": "PROMOTION"

📦 SOCIAL
Email:
"Your friend Nikhil tagged you in a photo. See what he said about your birthday dinner!"

How you should interpret this:
It’s a social media alert. The sender is an app, not a person — and there’s no business context or action.

Correct Classification:
→ "label": "no", "subtype": "SOCIAL"

yaml
Copy
Edit

---

🔐 DEADLINE DETECTION (due_time):
- Extract this ONLY if the email says something like:
  - "Due by June 15th"
  - "Submit before 5PM tomorrow"
  - "Deadline: Monday, 3PM IST"
- Format: `"due_time": "2025-06-10T17:00:00Z"`
- Skip this field if no specific time is mentioned.

---

🎯 OUTPUT FORMAT:

Respond ONLY with this valid JSON block:
{
  "label": "<email | notify | no>",
  "subtype": "<exact_subtype>",
  "due_time": "..." // optional
}

❌ Do NOT explain your answer.  
❌ Do NOT use markdown or return summaries.  
✅ Only return the JSON object.

---

📩 EMAIL TO TRIAGE:
\"\"\"
{email_content}
\"\"\"

📤 FINAL ANSWER:
"""


def classify_email(email_body: str) -> dict:
    """Returns classification label, subtype, and metadata as a dict."""
    try:
        if not email_body.strip():
            return {"label": "notify", "subtype": "UPCOMING_EVENT"}

        input_prompt = TRIAGE_PROMPT_TEMPLATE.format(email_content=email_body)

        response = llm.invoke([{"role": "user", "content": input_prompt}])
        raw_response = response.content.strip()

        match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return {
                "label": data.get("label", "notify").lower(),
                "subtype": data.get("subtype", "UPCOMING_EVENT").upper(),
                "due_time": data.get("due_time") or data.get("meeting_time")
            }

        logger.warning(f"⚠️ Unexpected format: {raw_response}")
        return {"label": "notify", "subtype": "UPCOMING_EVENT"}

    except Exception as e:
        logger.error(f"❌ Error in classify_email: {e}")
        return {"label": "notify", "subtype": "UPCOMING_EVENT"}
