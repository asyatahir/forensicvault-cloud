"""Structured Carousell listing evidence extraction."""

import json
import hashlib
import re

from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from url_validator import valid_case_id


def extract_listing_data(html_content):

    soup = BeautifulSoup(html_content, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else ""

    blocked_indicators = [
        "just a moment",
        "verify you are human",
        "access denied",
        "checking your browser"
    ]

    if any(x in title.lower() for x in blocked_indicators):
        raise RuntimeError("Security verification page detected.")

    def get_meta(key):
        tag = soup.find("meta", property=key)
        return tag.get("content") if tag else None

    product = None

    for script in soup.find_all(
        "script", type="application/ld+json"
    ):
        try:
            data = json.loads(script.get_text())

            if isinstance(data, dict):
                if data.get("@type") == "Product":
                    product = data
                    break

        except (ValueError, TypeError):
            continue

    if not product or not product.get("name"):
        raise RuntimeError("No valid product data found.")

    offers = product.get("offers", {})

    if not isinstance(offers, dict):
        offers = {}

    images = product.get("image", [])

    if isinstance(images, str):
        images = [images]

    if not isinstance(images, list):
        images = []

    images = [x for x in images if isinstance(x, str)]

    canonical = soup.find("link", rel="canonical")

    source_url = (
        canonical.get("href") if canonical else None
    ) or get_meta("og:url")

    listing_id = None

    if source_url:
        path = urlparse(source_url).path

        match = re.search(
            r"(?:-|/)(\d+)/?$", path
        )

        if match:
            listing_id = match.group(1)

    return {
        "platform": "Carousell",
        "listing_id": listing_id,
        "source_url": source_url,
        "product_name": product.get("name"),
        "description": product.get("description"),
        "price": offers.get("price"),
        "currency": offers.get("priceCurrency"),
        "availability": offers.get("availability"),
        "condition": offers.get("itemCondition"),
        "image_count": len(images),
        "image_urls": images,
        "images_downloaded": False
    }


def generate_listing_evidence(
    html_path,
    case_id,
    requested_url=None,
    captured_at=None
):

    if not valid_case_id(case_id):
        raise ValueError("Invalid case ID.")

    source = Path(html_path)

    html_content = source.read_bytes()

    listing = extract_listing_data(html_content)

    if requested_url is not None:
        validate_listing_identity(
            requested_url,
            listing["source_url"]
        )

    listing["requested_url"] = requested_url

    listing["case_id"] = case_id

    listing["processed_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    listing["collection_method"] = "Saved HTML extraction"

    listing["source_filename"] = source.name

    listing["source_sha256"] = hashlib.sha256(
        html_content
    ).hexdigest()

    listing["original_capture_time"] = captured_at

    if captured_at is not None:
        listing["collection_method"] = (
            "Browser capture and structured HTML extraction"
        )

    output_path = source.with_name(
        f"{source.stem}_{case_id}_listing.json"
    )

    with output_path.open("x", encoding="utf-8") as f:
        json.dump(
            listing,
            f,
            indent=4,
            ensure_ascii=False
        )

    return output_path, listing


def get_listing_identity(url):

    if not isinstance(url, str):
        raise ValueError("Missing listing URL.")

    parsed = urlparse(url)

    allowed_hosts = {
        "carousell.com.my",
        "www.carousell.com.my",
        "carousell.sg",
        "www.carousell.sg"
    }

    if (
        parsed.scheme != "https"
        or parsed.hostname not in allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ValueError("Invalid Carousell listing URL.")

    match = re.fullmatch(
        r"/p/(?:[^/]+-)?([0-9]+)/?",
        parsed.path
    )

    if not match:
        raise ValueError("Invalid Carousell listing path.")

    domain = parsed.hostname

    if domain.startswith("www."):
        domain = domain[4:]

    return domain, match.group(1)


def validate_listing_identity(requested_url, captured_url):

    requested = get_listing_identity(requested_url)
    captured = get_listing_identity(captured_url)

    if requested != captured:
        raise RuntimeError(
            "Captured listing does not match requested listing."
        )

    return True
