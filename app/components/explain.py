import re

keywords = [
    "verify",
    "verification",
    "password",
    "login",
    "account",
    "suspended",
    "suspension",
    "urgent",
    "urgently"
    "immediately",
    "click here",
    "click the link",
    "security",
    "payment",
    "invoice",
    "confirm",
]


def explain_email(request):
    reasons = []
    triggers = []

    text = (
            request.subject +
            " " +
            request.body
    ).lower()

    # url detection
    if re.search(r"https?://\S+", text):
        reasons.append("Contains external links / URLs.")

    # language
    for word in keywords:
        if word in text:
            triggers.append(word)

    if triggers:
        reasons.append("Contains common phishing language.")

    # sender address
    sender = request.sender_email.lower()

    if any(char.isdigit() for char in text):
        reasons.append("Sender address contains digits.")

    if "-" in sender:
        reasons.append("Sender address contains hyphens.")

    if not request.sender_display_name:
        reasons.append("Sender does not have a display name.")

    username, domain = sender.split("@", 1)
    if len(username) >= 12:
        reasons.append("Sender's username is long.")

    if len(domain) >= 16:
        reasons.append("Sender's domain address is long.")

    return {
        "reasons": reasons,
        "trigger_words": triggers,
    }
