# tools/send_gmail.py
# Purpose: Send an email with a PDF attachment via Gmail API (shared OAuth token with Drive)
# Inputs: to_email, subject, body, cv_path
# Outputs: message id on success, raises on failure

import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_gmail_service():
    from download_cvs import get_drive_service
    _, creds = get_drive_service()
    return build("gmail", "v1", credentials=creds)


def send_email(to_email: str, subject: str, body: str, cv_path: str, html: str = None) -> str:
    sender = os.getenv("GMAIL_SENDER", "shawada6@gmail.com")

    msg = MIMEMultipart("mixed")
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject

    # Multipart/alternative for plain + HTML
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body, "plain", "utf-8"))
    if html:
        alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    with open(cv_path, "rb") as f:
        pdf_data = f.read()
    attachment = MIMEApplication(pdf_data, _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(cv_path))
    msg.attach(attachment)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service = get_gmail_service()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result["id"]


if __name__ == "__main__":
    cv_path = os.path.join(BASE_DIR, ".tmp", "cvs", "Omar_Shawada_Operations_CV_ATS.pdf")
    msg_id = send_email(
        to_email="shawada6@gmail.com",
        subject="Test Application",
        body="This is a test email body.",
        cv_path=cv_path,
    )
    print(f"Sent! Message ID: {msg_id}")
