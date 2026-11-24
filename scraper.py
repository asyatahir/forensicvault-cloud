
import os
import time
import hashlib
import shutil
import uuid

from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

STORAGE_VAULT = "local_vault"


def setup_driver():

    if os.getenv(
        "ENABLE_BROWSER_COLLECTION", "false"
    ).lower() != "true":
        raise RuntimeError(
            "Automatic browser collection is disabled. "
            "Please use manual evidence upload."
        )

    chrome_options = Options()

    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--window-size=1920,1080")

    chromium = (
        shutil.which("chromium")
        or shutil.which("chromium-browser")
    )

    chromedriver = shutil.which("chromedriver")

    if chromium and chromedriver:

        chrome_options.binary_location = chromium
        service = Service(chromedriver)

    else:

        service = Service(
            ChromeDriverManager().install()
        )

    driver = webdriver.Chrome(
        service=service,
        options=chrome_options
    )

    driver.set_page_load_timeout(60)

    return driver


def extract_evidence(driver, target_url, case_id):

    from carousell_collector import (
        get_listing_identity,
        validate_listing_identity,
        generate_listing_evidence
    )
    from url_validator import valid_case_id

    if not valid_case_id(case_id):
        raise ValueError("Invalid case ID.")

    get_listing_identity(target_url)

    os.makedirs(STORAGE_VAULT, exist_ok=True)

    driver.get(target_url)

    time.sleep(8)

    validate_listing_identity(
        target_url,
        driver.current_url
    )

    # Detect security verification and blocked pages
    page_title = driver.title.lower()
    page_text = driver.find_element("tag name", "body").text.lower()

    blocked_indicators = [
        "performing security verification",
        "verify you are human",
        "checking your browser",
        "just a moment",
        "access denied",
        "attention required",
        "captcha",
        "403 forbidden"
    ]

    if any(
        indicator in page_title or indicator in page_text
        for indicator in blocked_indicators
    ):
        raise RuntimeError(
            "Automatic collection blocked by website security. "
            "Please use manual evidence upload."
        )

    try:
        page_title = driver.title
    except Exception:
        page_title = "Title extraction failed"

    captured_at = datetime.now(timezone.utc)

    timestamp = captured_at.strftime(
        "%Y%m%d_%H%M%S"
    )

    capture_id = uuid.uuid4().hex[:12]

    screenshot_path = os.path.join(
        STORAGE_VAULT,
        f"{case_id}_{timestamp}_{capture_id}_screenshot.png"
    )

    html_path = os.path.join(
        STORAGE_VAULT,
        f"{case_id}_{timestamp}_{capture_id}_source.html"
    )

    if not driver.save_screenshot(screenshot_path):
        raise RuntimeError("Screenshot capture failed.")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    json_path, listing = generate_listing_evidence(
        html_path,
        case_id,
        requested_url=target_url,
        captured_at=captured_at.isoformat()
    )

    return {
        "case_id": case_id,
        "target_url": target_url,
        "title": listing["product_name"],
        "screenshot_path": screenshot_path,
        "html_path": html_path,
        "artifact_paths": [
            screenshot_path,
            html_path,
            str(json_path)
        ],
        "extraction_date": captured_at.isoformat()
    }


def generate_file_hash(file_path):

    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:

        for byte_block in iter(
            lambda: f.read(4096), b""
        ):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()
