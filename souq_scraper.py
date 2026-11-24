import re
import uuid
import requests
from pathlib import Path
from datetime import datetime, timezone
from bs4 import BeautifulSoup

STORAGE_VAULT = Path("local_vault")


def extract_souq_evidence(target_url, case_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,50}", case_id):
        raise ValueError("Invalid case ID.")

    headers = {
        "User-Agent": "ForensicVault-FYP/1.0 (Academic Research Collector)"
    }
    max_size = 5 * 1024 * 1024  # 5 MB limit

    with requests.get(
        target_url,
        headers=headers,
        timeout=(10, 30),
        allow_redirects=True,
        stream=True,
    ) as response:
        if response.status_code != 200:
            raise RuntimeError(
                f"IIUM Souq page unavailable (HTTP {response.status_code})."
            )

        content = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            if len(content) + len(chunk) > max_size:
                raise RuntimeError("Response exceeds the 5 MB limit.")
            content.extend(chunk)

    html_content = bytes(content)
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract readable metadata and text
    page_title = (
        soup.title.get_text(strip=True)
        if soup.title else "IIUM Souq Listing"
    )

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    visible_text = soup.get_text("\n", strip=True)
    if not visible_text:
        raise RuntimeError("No readable content found on the Souq page.")

    STORAGE_VAULT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    capture_id = uuid.uuid4().hex[:12]

    filename = (
        f"{case_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        f"_{capture_id}_souq.txt"
    )
    log_path = STORAGE_VAULT / filename
    html_path = log_path.with_suffix(".html")

    html_path.write_bytes(html_content)

    with log_path.open("w", encoding="utf-8") as f:
        f.write("FORENSICVAULT - IIUM SOUQ EVIDENCE\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Case ID: {case_id}\n")
        f.write(f"Title: {page_title}\n")
        f.write(f"Source URL: {target_url}\n")
        f.write(f"Captured at: {timestamp.isoformat()}\n")
        f.write("Method: Public HTTP extraction\n")
        f.write("-" * 50 + "\n\n")
        f.write(visible_text)

    return {
        "case_id": case_id,
        "target_url": target_url,
        "title": page_title,
        "screenshot_path": str(log_path),
        "html_path": str(html_path),
        "extraction_date": timestamp.isoformat(),
    }