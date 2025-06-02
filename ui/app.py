import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from core.email_service import set_monitored_email, fetch_emails, send_email
from core.email_classifier import classify_email
from core.email_rewriter import rewrite_email
from core.ai_responder import draft_reply  # ✅ ADDED IMPORT
from core.database import session_scope, Email
from core.database import engine, Base

# Ensure tables are created
Base.metadata.create_all(bind=engine)

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for flash messages

# 📌 Load user settings
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "../.secrets/settings.json")


def get_monitored_email():
    """Retrieve the current monitored email from settings."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as file:
            settings = json.load(file)
            return settings.get("monitored_email", "Not Set")
    return "Not Set"


@app.route("/")
def index():
    """Home page displaying email settings and actions."""
    monitored_email = get_monitored_email()
    return render_template("index.html", monitored_email=monitored_email)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    """Set the monitored email through UI."""
    if request.method == "POST":
        email = request.form.get("email").strip()
        if email:
            set_monitored_email(email)
            flash(f"✅ Monitoring set to: {email}", "success")
            return redirect(url_for("index"))
        else:
            flash("❌ Please enter a valid email.", "danger")

    monitored_email = get_monitored_email()
    return render_template("settings.html", monitored_email=monitored_email)


import pprint  # Add this at the top

@app.route("/emails")
def emails():
    """Fetch emails and display them."""
    monitored_email = get_monitored_email()
    if monitored_email == "Not Set":
        flash("⚠ Please set a monitored email first.", "warning")
        return redirect(url_for("settings"))

    email_list = fetch_emails()  # Fetch latest emails (Already classified!)

    classified_emails = []
    for email in email_list:
        email_data = {
            "id": email.id,
            "from_email": email.from_addr,
            "subject": email.subject,
            "preview": email.snippet,
            "html_content": email.body,
            "classification": email.triage_label,
            "draft_reply": email.draft_reply  # ✅ ADDED THIS so Jinja can access
        }
        classified_emails.append(email_data)

    return render_template("emails.html", emails=classified_emails)

@app.route("/fetch", methods=["POST"])
def fetch():
    new_emails = fetch_emails()
    flash(f"✅ Fetched {len(new_emails)} new emails.", "success")
    return redirect(url_for("emails"))

@app.route("/send", methods=["GET", "POST"])
def send():
    """Send an email from UI."""
    if request.method == "POST":
        to_email = request.form.get("to_email").strip()
        subject = request.form.get("subject").strip()
        message_text = request.form.get("message").strip()

        if not to_email or not subject or not message_text:
            flash("❌ All fields are required.", "danger")
        else:
            success, response = send_email(to_email, subject, message_text)
            if success:
                flash(response, "success")
            else:
                flash(response, "danger")
        return redirect(url_for("send"))

    return render_template("send.html")

@app.route("/rewrite", methods=["GET", "POST"])
def rewrite_view():
    draft = ""
    tone = ""
    rewritten = ""
    tones = ["formal", "casual", "assertive", "friendly", "apologetic"]
    if request.method == "POST":
        draft = request.form.get("draft", "")
        tone = request.form.get("tone", "")
        if draft and tone:
            rewritten = asyncio.run(rewrite_email(draft, tone))
    return render_template("rewrite.html", draft=draft, tone=tone, tones=tones, rewritten=rewritten)

@app.route("/delete/<int:email_id>", methods=["POST"])
def delete_email(email_id):
    with session_scope() as db:
        email = db.query(Email).filter(Email.id == email_id).first()
        if email:
            db.delete(email)
            db.commit()
            flash(f"✅ Deleted email ID {email_id}", "success")
        else:
            flash(f"❌ Email ID {email_id} not found", "danger")
    return redirect(url_for("emails"))

# ✅ ✅ NEW ROUTE
@app.route("/generate_draft/<int:email_id>", methods=["POST"])
def generate_draft(email_id):
    with session_scope() as db:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            flash(f"❌ Email ID {email_id} not found.", "danger")
            return redirect(url_for("emails"))
        if not email.snippet:
            flash(f"⚠️ Email ID {email_id} has no snippet to summarize.", "warning")
            return redirect(url_for("emails"))
        try:
            generated_draft = draft_reply(email.snippet)
            email.draft_reply = generated_draft
            db.commit()
            flash(f"✅ Draft reply generated for email ID {email_id}.", "success")
        except Exception as e:
            flash(f"❌ Failed to generate draft: {e}", "danger")
    return redirect(url_for("emails"))

@app.route("/email/<int:email_id>")
def email_actions(email_id):
    with session_scope() as db:
        email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        flash(f"❌ Email ID {email_id} not found.", "danger")
        return redirect(url_for('emails'))
    return render_template("email_actions.html", email=email)

@app.route("/email/<int:email_id>/generate_draft", methods=["POST"])
def generate_draft_action(email_id):
    with session_scope() as db:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            flash(f"❌ Email ID {email_id} not found.", "danger")
            return redirect(url_for('emails'))
        if not email.snippet:
            flash(f"⚠️ Email ID {email_id} has no snippet to summarize.", "warning")
            return redirect(url_for('email_actions', email_id=email_id))
        try:
            generated_draft = draft_reply(email.snippet)
            email.draft_reply = generated_draft
            db.commit()
            flash(f"✅ Draft generated!", "success")
        except Exception as e:
            flash(f"❌ Failed to generate draft: {e}", "danger")
    return redirect(url_for('email_actions', email_id=email_id))

@app.route("/email/<int:email_id>/rewrite", methods=["POST"])
def rewrite_draft_action(email_id):
    current_draft = request.form.get("current_draft", "")
    tone = request.form.get("tone", "polite and professional")
    if not current_draft:
        flash("⚠️ No draft provided to rewrite.", "warning")
        return redirect(url_for('email_actions', email_id=email_id))
    try:
        rewritten_text = asyncio.run(rewrite_email(current_draft, tone))
        with session_scope() as db:
            email = db.query(Email).filter(Email.id == email_id).first()
            if email:
                email.draft_reply = rewritten_text
                db.commit()
        flash(f"✅ Draft rewritten in {tone} tone!", "success")
    except Exception as e:
        flash(f"❌ Failed to rewrite draft: {e}", "danger")
    return redirect(url_for('email_actions', email_id=email_id))

@app.route("/email/<int:email_id>/send", methods=["POST"])
def send_reply_action(email_id):
    final_draft = request.form.get("final_draft", "")
    if not final_draft:
        flash("⚠️ Cannot send an empty reply.", "warning")
        return redirect(url_for('email_actions', email_id=email_id))
    with session_scope() as db:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            flash(f"❌ Email ID {email_id} not found.", "danger")
            return redirect(url_for('emails'))
        try:
            success, message = send_email(email.from_addr, f"RE: {email.subject}", final_draft)
            if success:
                email.sent = True
                db.commit()
                flash(f"✅ Reply sent!", "success")
            else:
                flash(f"❌ Failed to send: {message}", "danger")
        except Exception as e:
            flash(f"❌ Error sending email: {e}", "danger")
    return redirect(url_for('email_actions', email_id=email_id))


from core.calendar_manager import send_calendar_invite

@app.route("/email/<int:email_id>/schedule_meeting", methods=["POST"])
def schedule_meeting(email_id):
    recipient = request.form.get("recipient", "").strip()
    title = request.form.get("title", "Meeting with Anil").strip()
    date = request.form.get("date", "").strip()
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()

    if not all([recipient, date, start_time, end_time]):
        flash("❌ All meeting fields are required.", "danger")
        return redirect(url_for('email_actions', email_id=email_id))

    # Convert to ISO 8601 datetime
    try:
        start_iso = f"{date}T{start_time}:00"
        end_iso = f"{date}T{end_time}:00"

        success = send_calendar_invite(
            emails=[recipient],
            title=title,
            start_time=start_iso,
            end_time=end_iso
        )
        if success:
            flash(f"✅ Meeting invite sent to {recipient}!", "success")
        else:
            flash(f"❌ Failed to send meeting invite.", "danger")
    except Exception as e:
        flash(f"❌ Error scheduling meeting: {e}", "danger")

    return redirect(url_for("schedule_meeting_page", email_id=email_id))

@app.route("/email/<int:email_id>/action")
def route_email_action(email_id):
    with session_scope() as db:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            flash("❌ Email not found.", "danger")
            return redirect(url_for("emails"))

        label = email.triage_label or "notify"
        subtype = (email.triage_subtype or "").upper()

        # Try to load metadata from draft_reply (temporary hack until LLM flow improves)
        try:
            if email.draft_reply and "due_time" in email.draft_reply:
                import json
                meta = json.loads(email.draft_reply)
                due_time = meta.get("due_time")
        except Exception:
            pass

        # DEADLINE / REMINDER ACTIONS
        if subtype in ["DEADLINE_TASK", "REMINDER"]:
            if due_time:
                # Auto-create the reminder if metadata exists
                dt_obj = datetime.fromisoformat(due_time.replace("Z", ""))
                add_reminder(email_id=email.id, content=email.subject, due_time=dt_obj)
                flash("🔔 Reminder created automatically from email metadata.")
                return redirect(url_for("inbox"))
            else:
                return redirect(url_for("respond_to_email", email_id=email_id))

        elif label == "notify":
            # 🔜 Future: show /remind page
            flash("ℹ️ Notification saved. No reply needed.", "info")
            return redirect(url_for("emails"))

        else:
            flash("⚠️ This email does not require any action.", "warning")
            return redirect(url_for("emails"))


@app.route("/email/<int:email_id>/respond")
def respond_to_email(email_id):
    with session_scope() as db:
        email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        flash("❌ Email not found.", "danger")
        return redirect(url_for("emails"))
    return render_template("email_respond.html", email=email)


@app.route("/email/<int:email_id>/schedule")
def schedule_meeting_page(email_id):
    with session_scope() as db:
        email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        flash("❌ Email not found.", "danger")
        return redirect(url_for("emails"))
    return render_template("email_schedule.html", email=email)


if __name__ == "__main__":
    app.run(debug=True)
