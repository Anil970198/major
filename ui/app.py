import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from core.email_service import set_monitored_email, fetch_emails, send_email
from core.email_classifier import classify_email

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
            "from_email": email["from_email"],
            "subject": email["subject"],
            "preview": email.get("summary", "No summary available."),  # ✅ Use "summary"
            "html_content": email.get("html_content", ""),
            "classification": email.get("classification", "unknown"),
        }
        classified_emails.append(email_data)

    return render_template("emails.html", emails=classified_emails)


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


if __name__ == "__main__":
    app.run(debug=True)
