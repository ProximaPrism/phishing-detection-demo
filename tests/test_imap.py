from unittest.mock import Mock
from app.email_provider.imap import get_emails

def test_get_emails():
    # mocks imap to handle empty inboxes
    connection = Mock()

    connection.search.return_value = (
        "OK",
        [b"1 2"]
    )
    connection.fetch.return_value = (
        "OK",
        []
    )

    result = get_emails(connection)

    assert result == []