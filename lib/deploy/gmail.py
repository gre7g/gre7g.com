from aws_lambda_powertools import Logger
from email.message import EmailMessage
import logging
import os
import smtplib
import ssl

# Constants:
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)
GMAIL_ADDRESS = "gre7g.luterman@gmail.com"
SMTP_PORT = 587


def send_email_home(subject: str, message: str) -> bool:  # pragma: no cover
    """Send an e-mail to the site owner (returns success)"""
    try:

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = GMAIL_ADDRESS
        msg.set_content(message)

        context = ssl.create_default_context()
        with smtplib.SMTP(os.environ["GMAIL_SERVER"], SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(GMAIL_ADDRESS, os.environ["GMAIL_APP_PASSWORD"])
            server.send_message(msg)

        return True

    except:
        LOG.exception("Failed to send email")
        return False
