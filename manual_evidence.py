import hashlib
import uuid

from pathlib import Path
from datetime import datetime, timezone

from cloud_storage import upload_evidence, download_evidence
from collection_database import (
    save_collected_evidence,
    update_blockchain_status
)
from blockchain import store_on_blockchain


def preserve_manual_evidence(
    uploaded_file, case_id, platform, target_url, notes
):
    filename = Path(uploaded_file.name).name
    extension = Path(filename).suffix.lower()

    if extension not in {
        ".png", ".jpg", ".jpeg", ".pdf", ".txt", ".html"
    }:
        raise ValueError("Unsupported evidence file type.")

    file_bytes = uploaded_file.getvalue()

    if not file_bytes:
        raise ValueError("Evidence file is empty.")

    if len(file_bytes) > 10 * 1024 * 1024:
        raise ValueError("Evidence exceeds 10 MB.")

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    object_path = (
        f"captured_evidence/{uuid.uuid4().hex}{extension}"
    )

    upload_evidence(
        file_bytes, object_path, "application/octet-stream"
    )

    downloaded_bytes = download_evidence(object_path)

    if hashlib.sha256(downloaded_bytes).hexdigest() != file_hash:
        raise RuntimeError("Cloud integrity verification failed.")

    metadata = {
        "original_filename": filename,
        "file_path": f"supabase://{object_path}",
        "sha256": file_hash,
        "captured_at": datetime.now(timezone.utc).isoformat()
    }

    evidence_id = save_collected_evidence(
        case_id=case_id,
        platform=platform,
        target_url=target_url,
        title="Manually submitted evidence",
        evidence=metadata,
        collection_method="Manual",
        investigation_notes=notes
    )

    metadata["id"] = evidence_id
    metadata["blockchain_status"] = "Pending"
    metadata["transaction_hash"] = None

    try:
        transaction_hash = store_on_blockchain(file_hash, case_id)
        metadata["transaction_hash"] = transaction_hash

        if update_blockchain_status(
            evidence_id, "Registered", transaction_hash
        ):
            metadata["blockchain_status"] = "Registered"

    except Exception:
        metadata["warning"] = "Registration requires confirmation."

    return metadata
