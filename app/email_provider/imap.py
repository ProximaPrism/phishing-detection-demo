import email
from email.header import decode_header
from email.utils import parseaddr
from typing import Optional

from bs4 import BeautifulSoup
from pydantic import BaseModel


class EmailResponse(BaseModel):
    id: str
    subject: str
    body: str
    sender_email: str
    sender_display_name: Optional[str]
    sent_datetime: str


def decode_text(value: str) -> str:
    if not value:
        return ""

    parts = decode_header(value)
    text = ""

    for part, encoding in parts:
        if isinstance(part, bytes):
            text += part.decode(
                encoding or "utf-8",
                errors="ignore"
            )
        else:
            text += part
    return text


def extract_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if "attachment" in str(part.get("Content-Disposition")):
                continue

            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)

            if payload is None:
                continue

            text = payload.decode(
                part.get_content_charset() or "utf-8",
                errors="ignore"
            )

            if content_type == "text/plain":
                return text

            # use bs4 to parse html into text
            if content_type == "text/html":
                body = BeautifulSoup(text, "html.parser").get_text()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(
                msg.get_content_charset() or "utf-8",
                errors="ignore"
            )
    return body


def get_emails(connection, offset: int = 0, limit: int = 10) -> list[EmailResponse]:
    connection.select("INBOX")

    status, data = connection.search(
        None,
        "ALL"
    )

    if status != "OK":
        return []

    emails = []
    email_ids = data[0].split()

    # newest emails first
    email_ids.reverse()

    # lazy loading slice
    id_slice = email_ids[offset:offset + limit]

    id_set = ",".join(
        email_id.decode()
        for email_id in id_slice
    )

    _, messages = connection.fetch(
        id_set,
        "(RFC822)"
    )

    # ensures correct order of emails
    email_map = {}

    for response in messages:
        # ignore IMAP metadata responses
        if not isinstance(response, tuple):
            continue

        msg = email.message_from_bytes(
            response[1]
        )
        display_name, sender = parseaddr(
            msg.get("From", "")
        )

        email_map[response[0].split()[0].decode()] = (
            EmailResponse(
                id=response[0].split()[0].decode(),
                subject=decode_text(
                    msg.get("Subject", "")
                ),
                body=extract_body(msg),
                sender_email=sender,
                sender_display_name=display_name,
                sent_datetime=msg.get(
                    "Date",
                    ""
                ),
            )
        )

    # restore original inbox order
    emails = [
        email_map[email_id.decode()]
        for email_id in id_slice
        if email_id.decode() in email_map
    ]
    return emails
