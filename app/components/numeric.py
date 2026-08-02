import numpy as np
import re
from email.utils import parseaddr
from datetime import datetime


def extract_numeric_features(request) -> dict:
    def parse_sender_receiver(raw: str) -> tuple[str, str]:
        n, e = parseaddr(raw)
        n = n.strip().replace('\\"', '"').strip('"').strip()
        e = e.lower().strip()
        return n, e

    def extract_email_components(e: str) -> tuple[str, str]:
        if '@' not in e:
            return "", ""
        u, d = e.split('@', 1)
        return u, d

    try:
        dt = datetime.strptime(request.sent_datetime,"%Y-%m-%d %H:%M:%S")
        is_date_invalid = 0

        hour = dt.hour
        day_of_week = dt.weekday()

        hour_sin = np.sin(2 * np.pi * hour / 24.0)
        hour_cos = np.cos(2 * np.pi * hour / 24.0)

        day_of_week_sin = np.sin(2 * np.pi * day_of_week / 7.0)
        day_of_week_cos = np.cos(2 * np.pi * day_of_week / 7.0)
    except ValueError:
        is_date_invalid = 1
        hour_sin = 0
        hour_cos = 0

        day_of_week_sin = 0
        day_of_week_cos = 0

    display_name, email = parse_sender_receiver(request.sender_email)
    is_sender_displayname_missing = (len(display_name) == 0) * 1
    is_sender_email_missing = ('@' not in email) * 1
    sender_email_digit_count =  sum(char.isdigit() for char in email)
    sender_email_has_hyphens = ('-' in email) * 1

    username, domain = extract_email_components(email)
    sender_username_length = len(username)
    sender_domain_length = len(domain)

    does_body_contains_urls = bool(re.search(r"https://\S+", request.body)) * 1

    return {
        "is_date_invalid": is_date_invalid,
        "is_sender_displayname_missing": is_sender_displayname_missing,
        "is_sender_email_missing": is_sender_email_missing,
        "sender_email_digit_count": sender_email_digit_count,
        "sender_email_has_hyphens": sender_email_has_hyphens,
        "sender_username_length": sender_username_length,
        "sender_domain_length": sender_domain_length,
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
        "day_of_week_sin": day_of_week_sin,
        "day_of_week_cos": day_of_week_cos,
        "does_body_contains_urls": does_body_contains_urls
    }