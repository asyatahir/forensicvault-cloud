
from pathlib import Path
from cloud_storage import download_evidence

LOCAL_ROOT = Path("local_vault/victim_uploads").resolve()


def read_evidence(file_path):

    file_path = str(file_path)

    # Retrieve cloud evidence
    if file_path.startswith("supabase://"):

        object_path = file_path[len("supabase://"):]

        if not object_path.startswith(
            ("victim_uploads/", "captured_evidence/")
        ):
            raise ValueError("Invalid cloud evidence path.")

        if ".." in object_path.split("/"):
            raise ValueError("Invalid evidence path.")

        return download_evidence(object_path)

    # Retrieve existing local evidence
    local_path = Path(file_path).resolve()

    if not local_path.is_relative_to(LOCAL_ROOT):
        raise ValueError("Invalid local evidence path.")

    if not local_path.is_file():
        raise FileNotFoundError("Evidence file not found.")

    return local_path.read_bytes()
