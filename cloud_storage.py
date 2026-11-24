
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
BUCKET_NAME = os.getenv("SUPABASE_BUCKET", "forensic-evidence")


def get_storage():

    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise RuntimeError("Supabase credentials are missing.")

    client = create_client(
        SUPABASE_URL,
        SUPABASE_SECRET_KEY
    )

    return client.storage.from_(BUCKET_NAME)


def upload_evidence(file_bytes, object_path,
                    content_type="application/octet-stream"):

    storage = get_storage()

    storage.upload(
        path=object_path,
        file=file_bytes,
        file_options={
            "content-type": content_type,
            "upsert": "false"
        }
    )

    return object_path


def download_evidence(object_path):

    storage = get_storage()

    return storage.download(object_path)
