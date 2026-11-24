
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from cloud_storage import upload_evidence, download_evidence

EVIDENCE_FOLDER = Path("local_vault") / "victim_uploads"

ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".pdf", ".txt"
}

MAX_FILE_SIZE = 10 * 1024 * 1024

CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".html": "text/html"
}


def save_victim_evidence(uploaded_file):

    if uploaded_file is None:
        return None

    extension = Path(uploaded_file.name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type.")

    file_bytes = uploaded_file.getvalue()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError("File exceeds the 10 MB limit.")

    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    file_id = uuid.uuid4().hex

    object_path = f"victim_uploads/{file_id}{extension}"

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    upload_evidence(
        file_bytes,
        object_path,
        CONTENT_TYPES[extension]
    )

    return {
        "file_path": f"supabase://{object_path}",
        "sha256": file_hash,
        "captured_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "original_filename": Path(uploaded_file.name).name
    }



def save_captured_evidence(source_path):

    source_path = Path(source_path)

    if not source_path.is_file():
        raise FileNotFoundError(
            "Captured evidence file not found."
        )

    extension = source_path.suffix.lower()

    if extension not in {".png", ".html", ".txt"}:
        raise ValueError(
            "Unsupported captured evidence type."
        )

    file_bytes = source_path.read_bytes()

    if not file_bytes:
        raise ValueError("Captured evidence file is empty.")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError("Captured evidence exceeds 10 MB.")

    file_id = uuid.uuid4().hex

    object_path = f"captured_evidence/{file_id}{extension}"

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    upload_evidence(
        file_bytes,
        object_path,
        CONTENT_TYPES[extension]
    )

    # Verify evidence integrity after cloud upload
    downloaded_bytes = download_evidence(object_path)

    downloaded_hash = hashlib.sha256(
        downloaded_bytes
    ).hexdigest()

    if downloaded_hash != file_hash:
        raise RuntimeError(
            "Cloud evidence integrity verification failed."
        )

    return {
        "file_path": f"supabase://{object_path}",
        "sha256": file_hash,
        "captured_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "original_filename": source_path.name
    }
