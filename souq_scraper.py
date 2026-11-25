import json
import hashlib
import re
import uuid
import requests
from pathlib import Path
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from url_validator import normalize_souq_url

STORAGE_VAULT = Path("local_vault")


def extract_souq_evidence(target_url, case_id):

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,50}", case_id):
        raise ValueError("Invalid case ID.")

    target_url = normalize_souq_url(target_url)

    headers = {
        "User-Agent": "ForensicVault-FYP/1.0 (Academic Research Collector)"
    }

    max_size = 5 * 1024 * 1024

    try:
        with requests.get(
            target_url,
            headers=headers,
            timeout=(10, 30),
            allow_redirects=False,
            stream=True,
        ) as response:

            if 300 <= response.status_code < 400:
                raise RuntimeError(
                    "IIUM Souq returned a redirect. "
                    "Use the direct approved listing URL."
                )

            if response.status_code in (401, 403, 429):
                raise RuntimeError(
                    "IIUM Souq access is restricted or rate limited."
                )

            if response.status_code != 200:
                raise RuntimeError(
                    f"IIUM Souq unavailable "
                    f"(HTTP {response.status_code})."
                )

            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            if "text/html" not in content_type:
                raise RuntimeError(
                    "Expected an HTML webpage."
                )

            content = bytearray()

            for chunk in response.iter_content(
                chunk_size=65536
            ):
                if len(content) + len(chunk) > max_size:
                    raise RuntimeError(
                        "Response exceeds the 5 MB limit."
                    )

                content.extend(chunk)

    except requests.exceptions.Timeout as error:
        raise RuntimeError(
            "IIUM Souq connection timed out. "
            "Check authorized campus network access."
        ) from error

    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "Unable to connect to IIUM Souq. "
            "Check authorized campus network access."
        ) from error

    if not content:
        raise RuntimeError("Empty webpage response.")

    html_content = bytes(content)
    soup = BeautifulSoup(html_content, "html.parser")

    page_title = (
        soup.title.get_text(strip=True)
        if soup.title else "IIUM Souq Listing"
    )

    blocked_titles = (
        "access denied",
        "just a moment",
        "verify you are human",
        "checking your browser",
        "login",
        "log in",
        "sign in",
        "forbidden",
        "service unavailable",
    )

    if any(
        indicator in page_title.lower()
        for indicator in blocked_titles
    ):
        raise RuntimeError(
            "Access restriction or login page detected."
        )

    if soup.select_one('input[type="password"]'):
        raise RuntimeError(
            "Authentication page detected."
        )

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    visible_text = soup.get_text("\n", strip=True)

    if not visible_text:
        raise RuntimeError(
            "No readable content found on the Souq page."
        )

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
        f.write("Method: HTTP extraction\n")
        f.write("Listing verification: Unverified\n")
        f.write("-" * 50 + "\n\n")
        f.write(visible_text)

    json_path = log_path.with_suffix(".json")

    metadata = {
        "schema_version": "1.0",
        "project": "ForensicVault",
        "platform": "IIUM Souq",
        "case_id": case_id,
        "capture_id": capture_id,
        "source_url": target_url,
        "page_title": page_title,
        "captured_at": timestamp.isoformat(),
        "collection_method": "HTTP extraction",
        "listing_verification": "Unverified",
        "product_name": None,
        "product_price": None,
        "product_description": None,
        "product_image_url": None,
        "artifacts": {
            "html": {
                "filename": html_path.name,
                "sha256": hashlib.sha256(
                    html_path.read_bytes()
                ).hexdigest(),
            },
            "text": {
                "filename": log_path.name,
                "sha256": hashlib.sha256(
                    log_path.read_bytes()
                ).hexdigest(),
            },
        },
    }

    with json_path.open("x", encoding="utf-8") as f:
        json.dump(
            metadata,
            f,
            indent=4,
            ensure_ascii=False,
        )

    return {
        "case_id": case_id,
        "target_url": target_url,
        "title": page_title,
        "artifact_paths": [
            str(html_path),
            str(log_path),
            str(json_path),
        ],
        "extraction_date": timestamp.isoformat(),
    }
