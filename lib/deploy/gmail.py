"""Utilities for sending notification e-mail to the site owner through Gmail's SMTP server"""

from aws_lambda_powertools import Logger
from email.message import EmailMessage
import logging
import os
import smtplib
import ssl

# Constants:
# Use the Powertools structured logger when running inside Lambda, plain stdlib logging otherwise (tests, local runs).
LOG = Logger(__name__) if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else logging.getLogger(__name__)
GMAIL_ADDRESS = "gre7g.luterman@gmail.com"  # Used as sender, recipient, and SMTP login
SMTP_PORT = 587  # SMTP submission port; the connection starts in plaintext and is upgraded with STARTTLS


def send_email_home(subject: str, message: str) -> bool:  # pragma: no cover
    """Send an e-mail to the site owner (returns success)

    Requires the "GMAIL_SERVER" and "GMAIL_APP_PASSWORD" environment variables. The password must be a Google
    "app password", since Gmail rejects plain account passwords for SMTP logins.

    Args:
        subject: Subject line of the message.
        message: Plain-text body of the message.

    Returns:
        True if the message was handed off to the SMTP server, False on any failure. Failures (including missing
        environment variables) are logged and never raised, so a mail problem can't fail the calling request.
    """
    try:

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = GMAIL_ADDRESS
        msg.set_content(message)

        context = ssl.create_default_context()
        with smtplib.SMTP(os.environ["GMAIL_SERVER"], SMTP_PORT) as server:
            # EHLO must be repeated after STARTTLS: the server re-advertises its capabilities (including AUTH) only
            # over the encrypted channel.
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(GMAIL_ADDRESS, os.environ["GMAIL_APP_PASSWORD"])
            server.send_message(msg)

        return True

    except:
        LOG.exception("Failed to send email")
        return False
