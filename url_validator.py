import re
from urllib.parse import urlparse


from urllib.parse import urlsplit


def validate_carousell_url(url):
    try:
        parsed = urlsplit(url.strip())

        if parsed.scheme != "https":
            return False

        if parsed.username or parsed.password:
            return False

        if parsed.port is not None:
            return False

        hostname = (parsed.hostname or "").lower().rstrip(".")

        allowed_domains = (
            "carousell.com.my",
            "www.carousell.com.my",
            "carousell.sg",
            "www.carousell.sg",
        )

        if hostname not in allowed_domains:
            return False

        if not parsed.path or parsed.path == "/":
            return False

        return True

    except ValueError:
        return False

def valid_case_id(case_id):
    return bool(
        re.fullmatch(
            r"[A-Za-z0-9_-]{1,50}",
            case_id
        )
    )
def normalize_carousell_url(value):
    value = value.strip()
    if not value.startswith(("https://", "http://")):
        value = "https://" + value
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    allowed_domains = (
        "carousell.com",
        "carousell.com.my",
        "carousell.sg",
        "carousell.ph",
        "carousell.hk",
        "carousell.tw",
        "carousell.id",
    )
    allowed = any(
        host == domain or host.endswith("." + domain)
        for domain in allowed_domains
    )
    if (
        parsed.scheme != "https"
        or not allowed
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(
            "Please enter a valid HTTPS Carousell URL."
        )
    try:
        if parsed.port not in (None, 443):
            raise ValueError("Unexpected URL port.")
    except ValueError:
        raise ValueError("Invalid Carousell URL port.")
    return value
def normalize_telegram_target(value):
    value = value.strip()
    if value.startswith("@"):
        value = value[1:]
    if value.startswith(("https://", "http://")):
        parsed = urlparse(value)
        if (
            parsed.scheme != "https"
            or (parsed.hostname or "").lower()
            not in ("t.me", "www.t.me")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "Use a public Telegram channel link."
            )
        value = parsed.path.strip("/")
    if not re.fullmatch(
        r"[A-Za-z0-9_]{5,32}",
        value
    ):
        raise ValueError(
            "Enter a valid public Telegram channel username."
        )
    return value


def normalize_souq_url(value):
    value = value.strip()

    if not value.startswith(("https://", "http://")):
        value = "https://" + value

    try:
        parsed = urlsplit(value)

        if (
            parsed.scheme != "https"
            or parsed.hostname not in (
                "souq.iium.edu.my",
                "www.souq.iium.edu.my",
            )
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
            or not parsed.path
            or parsed.path == "/"
            or parsed.fragment
        ):
            raise ValueError("Invalid IIUM Souq URL.")

    except ValueError:
        raise ValueError(
            "Please enter a valid HTTPS IIUM Souq listing URL."
        )

    return value
