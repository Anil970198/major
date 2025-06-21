import ollama

email_html = """.awl a {color: #FFFFFF; text-decoration: none;} .abml a {color: #000000; font-family: Roboto-Medium,Helvetica,Arial,sans-serif; font-weight: bold; text-decoration: none;} .adgl a {color: rgba(0, 0, 0, 0.87); text-decoration: none;} .afal a {color: #b0b0b0; text-decoration: none;} @media screen and (min-width: 600px) {.v2sp {padding: 6px 30px 0px;} .v2rsp {padding: 0px 10px;}} @media screen and (min-width: 600px) {.mdv2rw {padding: 40px 40px;}} Email Assistant was granted access to your Google Account mondruanilkumar596@gmail.com If you did not grant access, you should check this activity and secure your account.Check activityYou can also see security activity athttps://myaccount.google.com/notificationsYou received this email to let you know about important changes to your Google Account and services.© 2025 Google LLC, 1600 Amphitheatre Parkway, Mountain View, CA 94043, USA"""  # Replace this with your sample email

prompt = f"""
You are an AI email assistant. Your job is to **read and summarize** email content accurately.

- **Extract useful information from the email body.**
- **Ignore decorative elements (buttons, styling, metadata).**
- **If links exist, include them in parentheses (e.g., 'Check here (https://example.com)').**
- **If the email has structured data (like a receipt or event), summarize key details.**
- **Ensure the summary is structured, easy to read, and fully captures the email's purpose.**

Here is the email content:
{email_html}

Provide a **clean and well-structured summary**:
"""

response = ollama.chat(model="mistral", messages=[{"role": "user", "content": prompt}])
print("\n📩 **Summarized Email:**\n")
print(response["message"]["content"])
