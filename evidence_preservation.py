
from datetime import datetime, timezone

from victim_evidence import save_captured_evidence

from collection_database import (
    save_collected_evidence,
    update_blockchain_status
)

from blockchain import store_on_blockchain


def preserve_collected_evidence(evidence, platform):

    results = []

    artifact_paths = evidence.get("artifact_paths")

    if artifact_paths is None:
        artifact_paths = [
            evidence[key]
            for key in ("screenshot_path", "html_path")
            if evidence.get(key)
        ]

    if not isinstance(artifact_paths, (list, tuple)):
        raise ValueError("Invalid evidence artifact list.")

    if not artifact_paths:
        raise ValueError("No evidence artifacts available.")

    captured_at = evidence["extraction_date"]

    try:
        captured_at = datetime.fromisoformat(captured_at)
    except ValueError:
        captured_at = datetime.strptime(
            captured_at, "%Y%m%d_%H%M%S"
        )

    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(
            tzinfo=timezone.utc
        )

    for artifact_path in artifact_paths:

        # Upload and verify cloud evidence
        metadata = save_captured_evidence(
            artifact_path
        )

        metadata["captured_at"] = (
            captured_at.isoformat()
        )

        # Record evidence metadata
        evidence_id = save_collected_evidence(
            case_id=evidence["case_id"],
            platform=platform,
            target_url=evidence["target_url"],
            title=evidence["title"],
            evidence=metadata
        )

        metadata["id"] = evidence_id
        metadata["blockchain_status"] = "Pending"
        metadata["transaction_hash"] = None

        # Register evidence hash on Sepolia
        try:
            transaction_hash = store_on_blockchain(
                metadata["sha256"],
                evidence["case_id"]
            )

            metadata["transaction_hash"] = (
                transaction_hash
            )

            updated = update_blockchain_status(
                evidence_id,
                "Registered",
                transaction_hash
            )

            if not updated:
                raise RuntimeError(
                    "Database status update failed."
                )

            metadata["blockchain_status"] = "Registered"

        except Exception:
            metadata["warning"] = (
                "Blockchain registration requires "
                "manual confirmation."
            )

        results.append(metadata)

    return results
