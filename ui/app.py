import os
import json
import asyncio
from flask import Flask, render_template, request, redirect, url_for, flash
from core.email_service import set_monitored_email, fetch_emails, send_email
from core.email_classifier import classify_email
from core.email_rewriter import rewrite_email
from core.ai_responder import draft_reply  # ✅ ADDED IMPORT
from core.database import session_scope, Email
from core.database import engine, Base
from core.database import session_scope, Email, Reminder, Meeting
from core.database import log_meeting
from markupsafe import Markup
from core.helpers import markdownify


# Ensure tables are created
Base.metadata.create_all(bind=engine)

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.jinja_env.filters["markdown"] = lambda text: Markup(markdownify(text))


SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "../.secrets/settings.json")

def get_monitored_email():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as file:
            settings = json.load(file)
            return settings.get("monitored_email", "Not Set")
    return "Not Set"

@app.route("/")
def index():
    monitored_email = get_monitored_email()
    return render_template("index.html", monitored_email=monitored_email)

@app.route("/settings", methods=["GET", "POST"])
def settings():
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

@app.route("/emails")
def emails():
    monitored_email = get_monitored_email()
    if monitored_email == "Not Set":
        flash("⚠ Please set a monitored email first.", "warning")
        return redirect(url_for("settings"))
    with session_scope() as db:
        saved_emails = db.query(Email).order_by(Email.timestamp.desc()).all()
    classified_emails = []
    for email in saved_emails:
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
    if request.method == "POST":
        to_email = request.form.get("to_email", "").strip()
        subject = request.form.get("subject", "").strip()
        message_text = request.form.get("message", "").strip()
        if not to_email or not subject or not message_text:
            flash("❌ All fields are required.", "danger")
        else:
            success, response = send_email(to_email, subject, message_text)
            flash(response, "success" if success else "danger")
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

from core.database import session_scope, Email  # if not already imported

@app.route("/delete_all_emails", methods=["POST"])
def delete_all_emails():
    try:
        with session_scope() as session:
            session.query(Email).delete()
        flash("✅ All emails deleted.", "success")
    except Exception as e:
        flash(f"❌ Failed to delete emails: {e}", "danger")
    return redirect(url_for("emails"))

@app.route("/delete_all_reminders", methods=["POST"])
def delete_all_reminders():
    try:
        with session_scope() as session:
            session.query(Reminder).delete()
        flash("✅ All reminders deleted.", "success")
    except Exception as e:
        flash(f"❌ Failed to delete reminders: {e}", "danger")
    return redirect(url_for("emails"))

@app.route("/delete_all_meetings", methods=["POST"])
def delete_all_meetings():
    try:
        with session_scope() as session:
            session.query(Meeting).delete()
        flash("✅ All meetings deleted.", "success")
    except Exception as e:
        flash(f"❌ Failed to delete meetings: {e}", "danger")
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

# @app.route("/email/<int:email_id>")
# def email_actions(email_id):
#     with session_scope() as db:
#         email = db.query(Email).filter(Email.id == email_id).first()
#     if not email:
#         flash(f"❌ Email ID {email_id} not found.", "danger")
#         return redirect(url_for('emails'))
#     return render_template("email_actions.html", email=email)

@app.route("/email/<int:email_id>/generate_draft", methods=["POST"])
def generate_draft_action(email_id):
    with session_scope() as db:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            flash(f"❌ Email ID {email_id} not found.", "danger")
            return redirect(url_for('emails'))
        if not email.snippet:
            flash(f"⚠️ Email ID {email_id} has no snippet to summarize.", "warning")
            return redirect(url_for('respond_to_email', email_id=email_id))
        try:
            generated_draft = draft_reply(email.snippet)
            email.draft_reply = generated_draft
            db.commit()
            flash(f"✅ Draft generated!", "success")
        except Exception as e:
            flash(f"❌ Failed to generate draft: {e}", "danger")
    return redirect(url_for('respond_to_email', email_id=email_id))

@app.route("/email/<int:email_id>/rewrite", methods=["POST"])
def rewrite_draft_action(email_id):
    # ✅ Unified: use 'final_draft' for both send and rewrite
    current_draft = request.form.get("final_draft", "")
    tone = request.form.get("tone", "polite and professional")

    if not current_draft:
        flash("⚠️ No draft provided to rewrite.", "warning")
        return redirect(url_for('respond_to_email', email_id=email_id))

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

    return redirect(url_for('respond_to_email', email_id=email_id))

@app.route("/email/<int:email_id>/send", methods=["POST"])
def send_reply_action(email_id):
    final_draft = request.form.get("final_draft", "")
    if not final_draft:
        flash("⚠️ Cannot send an empty reply.", "warning")
        return redirect(url_for('respond_to_email', email_id=email_id))
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
    return redirect(url_for('respond_to_email', email_id=email_id))

from core.calendar_manager import schedule_meeting  # ✅ Correct function
from core.database import save_meeting  # ✅ To store Meet link

# Helper to fetch Gmail ID for saving meeting
def get_gmail_id(email_id):
    with session_scope() as db:
        email = db.query(Email).filter(Email.id == email_id).first()
        return email.gmail_id if email else None

@app.route("/email/<int:email_id>/schedule_meeting", methods=["POST"])
def schedule_meeting_route(email_id):
    recipient = request.form.get("recipient", "").strip()
    title = request.form.get("title", "Meeting with Anil").strip()
    date = request.form.get("date", "").strip()
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()

    if not all([recipient, date, start_time, end_time]):
        flash("❌ All meeting fields are required.", "danger")
        return redirect(url_for("schedule_meeting_page", email_id=email_id))

    try:
        start_iso = f"{date}T{start_time}:00"
        end_iso = f"{date}T{end_time}:00"

        result = schedule_meeting(
            emails=[recipient],
            title=title,
            start_time=start_iso,
            end_time=end_iso
        )

        if result.get("success"):
            meet_link = result.get("meet_link")

            # Optional: Save link in emails table
            save_meeting(gmail_id=get_gmail_id(email_id), link=meet_link)

            # ✅ REQUIRED: Add row to meetings table
            from datetime import datetime
            from core.database import log_meeting  # ✅ Ensure this is imported

            start_dt = datetime.fromisoformat(start_iso)
            end_dt = datetime.fromisoformat(end_iso)

            log_meeting(
                email_id=email_id,
                recipient=recipient,
                title=title,
                start=start_dt,
                end=end_dt,
                url=meet_link
            )

            flash(f"✅ Meeting invite sent to {recipient}! Google Meet link: {meet_link}", "success")

        else:
            flash(f"❌ Failed to schedule meeting: {result.get('error')}", "danger")

    except Exception as e:
        flash(f"❌ Error scheduling meeting: {e}", "danger")

    return redirect(url_for("schedule_meeting_page", email_id=email_id))

@app.route("/email/<int:email_id>/action")
def route_email_action(email_id):
    with session_scope() as db:
        email = db.query(Email).filter_by(id=email_id).first()
        if not email:
            flash("❌ Email not found.")
            return redirect(url_for("emails"))

        subtype = email.triage_subtype or ""
        due_time = None

        # Extract due_time (if embedded in draft_reply)
        try:
            if email.draft_reply and "due_time" in email.draft_reply:
                import json
                meta = json.loads(email.draft_reply)
                due_time = meta.get("due_time")
        except Exception:
            pass

        # 🔁 ROUTING LOGIC TABLE

        MEETING_SUBTYPES = {"MEETING_INVITE", "SCHEDULE_REQUEST"}
        RESPOND_SUBTYPES = {"INFO_REQUEST", "QUOTE_PROPOSAL", "SUPPORT_ISSUE", "FEEDBACK_COMPLAINT"}
        NOTIFY_ONLY = {"RESULT", "UPCOMING_EVENT", "ALERT"}
        IGNORE_TYPES = {"SPAM", "PROMOTION", "SOCIAL"}

        if subtype in MEETING_SUBTYPES:
            return redirect(url_for("schedule_meeting_page", email_id=email.id))

        if subtype in RESPOND_SUBTYPES:
            return redirect(url_for("respond_to_email", email_id=email.id))

        if due_time:
            return redirect(url_for("create_reminder", email_id=email.id))

        if subtype in NOTIFY_ONLY:
            flash(f"📌 Notification: {subtype.replace('_', ' ').title()}. No action needed.")
            return redirect(url_for("respond_to_email", email_id=email.id))

        if subtype in IGNORE_TYPES:
            flash("🚫 This email is classified as spam, promotional, or social.")
            return redirect(url_for("respond_to_email", email_id=email.id))

        # Fallback
        flash(f"⚠️ Unrecognized subtype: {subtype}")
        return redirect(url_for("respond_to_email", email_id=email.id))


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

        meetings = db.query(Meeting).filter_by(email_id=email.id).order_by(Meeting.start_time).all()
        done_meeting_ids = session.get("done_meeting_ids", [])

    print(f"🔍 DEBUG: Meetings for Email ID {email.id}")
    for m in meetings:
        print("•", m.title, m.start_time, m.calendar_url)

    return render_template(
        "email_schedule.html",
        email=email,
        meetings=meetings,
        done_meeting_ids=done_meeting_ids
    )



from flask import render_template, request, redirect, url_for, flash
from core.database import session_scope, Email, add_reminder
from datetime import datetime

from datetime import datetime, timedelta
from core.calendar_manager import add_calendar_reminder  # ✅ NEW IMPORT

@app.route("/reminder/<int:email_id>", methods=["GET", "POST"])
def create_reminder(email_id):
    with session_scope() as db:
        email = db.query(Email).filter_by(id=email_id).first()

        if not email:
            flash("Email not found.")
            return redirect(url_for("emails"))

        due_time_value = ""
        try:
            if email.draft_reply and "due_time" in email.draft_reply:
                import json
                meta = json.loads(email.draft_reply)
                raw = meta.get("due_time")
                if raw:
                    due_time_value = raw.replace("Z", "")[:16]
        except Exception:
            pass

        if request.method == "POST":
            content = request.form["content"]
            due_time = request.form["due_time"]
            due_time_parsed = datetime.strptime(due_time, "%Y-%m-%dT%H:%M")

            # Save to DB
            add_reminder(email_id=email.id, content=content, due_time=due_time_parsed)

            # ✅ Add to Google Calendar
            result = add_calendar_reminder(title=content, start_time=due_time_parsed.isoformat())
            if result.get("success"):
                flash("✅ Reminder created and added to Google Calendar.")
            else:
                flash(f"⚠️ Reminder saved, but Calendar failed: {result.get('error')}", "warning")

            return redirect(url_for("create_reminder", email_id=email.id))

        reminders = db.query(Reminder).filter_by(email_id=email.id).order_by(Reminder.due_time).all()
        done_ids = session.get("done_ids", [])

        return render_template(
            "email_reminder.html",
            email=email,
            due_time=due_time_value,
            reminders=reminders,
            done_ids=done_ids
        )

from flask import session

@app.route("/toggle_reminder", methods=["POST"])
def toggle_reminder():
    reminder_id = request.form.get("done_id", type=int)
    if not reminder_id:
        flash("⚠️ Invalid reminder toggle.", "warning")
        return redirect(url_for("emails"))

    if "done_ids" not in session:
        session["done_ids"] = []

    done_ids = session["done_ids"]

    if reminder_id in done_ids:
        # Second click → delete
        with session_scope() as db:
            reminder = db.query(Reminder).filter_by(id=reminder_id).first()
            if reminder:
                db.delete(reminder)
                db.commit()
        done_ids.remove(reminder_id)
        flash("🗑 Reminder deleted.")
    else:
        # First click → mark done
        done_ids.append(reminder_id)
        flash("✅ Reminder marked as done.")

    session["done_ids"] = done_ids
    return redirect(request.referrer or url_for("emails"))

@app.route("/toggle_meeting", methods=["POST"])
def toggle_meeting():
    meeting_id = request.form.get("done_id", type=int)
    email_id = request.form.get("email_id", type=int)

    if not meeting_id or not email_id:
        flash("⚠️ Invalid meeting toggle.", "warning")
        return redirect(url_for("emails"))

    if "done_meeting_ids" not in session:
        session["done_meeting_ids"] = []

    done_meeting_ids = session["done_meeting_ids"]

    if meeting_id in done_meeting_ids:
        with session_scope() as db:
            meeting = db.query(Meeting).filter_by(id=meeting_id).first()
            if meeting:
                db.delete(meeting)
                db.commit()
        done_meeting_ids.remove(meeting_id)
        flash("🗑 Meeting deleted.")
    else:
        done_meeting_ids.append(meeting_id)
        flash("✅ Meeting marked as done.")

    session["done_meeting_ids"] = done_meeting_ids
    return redirect(url_for("schedule_meeting_page", email_id=email_id))

@app.route("/dashboard")
def dashboard():
    with session_scope() as db:
        meetings = db.query(Meeting).order_by(Meeting.start_time).all()
        reminders = db.query(Reminder).order_by(Reminder.due_time).all()

    done_meeting_ids = session.get("done_meeting_ids", [])
    done_ids = session.get("done_ids", [])

    return render_template(
        "dashboard.html",
        meetings=meetings,
        reminders=reminders,
        done_meeting_ids=done_meeting_ids,
        done_ids=done_ids
    )



if __name__ == "__main__":
    app.run(debug=True)
