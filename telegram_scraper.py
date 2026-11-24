
import re
import uuid
import requests

from pathlib import Path
from datetime import datetime, timezone
from bs4 import BeautifulSoup

STORAGE_VAULT = Path("local_vault")


def extract_telegram_evidence(target_channel, case_id):

    channel = target_channel.strip()

    if channel.startswith("https://t.me/s/"):
        channel = channel[len("https://t.me/s/"):]

    elif channel.startswith("https://t.me/"):
        channel = channel[len("https://t.me/"):]

    channel = channel.strip("/").lstrip("@")

    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", channel):
        raise ValueError("Invalid public Telegram channel.")

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,50}", case_id):
        raise ValueError("Invalid case ID.")

    public_url = f"https://t.me/s/{channel}"

    max_size = 5 * 1024 * 1024

    with requests.get(
        public_url,
        timeout=(10, 30),
        allow_redirects=False,
        stream=True
    ) as response:

        if response.status_code != 200:
            raise RuntimeError(
                "Public Telegram preview unavailable."
            )

        content = bytearray()

        for chunk in response.iter_content(chunk_size=65536):
            if len(content) + len(chunk) > max_size:
                raise RuntimeError(
                    "Telegram response exceeds the allowed size."
                )

            content.extend(chunk)

    html_content = bytes(content)

    soup = BeautifulSoup(html_content, "html.parser")

    messages = soup.select(".tgme_widget_message")

    if not messages:
        raise RuntimeError("No publicly accessible messages found.")

    STORAGE_VAULT.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    capture_id = uuid.uuid4().hex[:12]

    filename = (
        f"{case_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        f"_{capture_id}_tg_chat.txt"
    )

    log_path = STORAGE_VAULT / filename

    html_path = log_path.with_suffix(".html")

    html_path.write_bytes(html_content)

    with log_path.open("w", encoding="utf-8") as f:

        f.write("FORENSICVAULT - PUBLIC TELEGRAM EVIDENCE\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Case ID: {case_id}\n")
        f.write(f"Channel: {channel}\n")
        f.write(f"Source URL: {public_url}\n")
        f.write(f"Captured at: {timestamp.isoformat()}\n")
        f.write("Method: Public web preview\n\n")

        for message in messages[-10:]:

            text = message.select_one(
                ".tgme_widget_message_text"
            )

            date = message.select_one("time")

            message_text = (
                text.get_text("\n", strip=True)
                if text else "[Media or no visible text]"
            )

            message_date = (
                date.get("datetime", "Unknown")
                if date else "Unknown"
            )

            post_id = message.get("data-post", "Unknown")

            f.write(f"Post: {post_id}\n")
            f.write(f"Date: {message_date}\n")
            f.write(f"Message: {message_text}\n")
            f.write("-" * 50 + "\n\n")

    return {
        "case_id": case_id,
        "target_url": public_url,
        "title": f"Telegram: {channel}",
        "screenshot_path": str(log_path),
        "html_path": str(html_path),
        "extraction_date": timestamp.isoformat()
    }
