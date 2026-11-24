import os
import re
import json
import uuid
import asyncio

from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Channel

load_dotenv(".env")

STORAGE_VAULT = Path("local_vault")


async def collect_messages(channel):

    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    session_string = os.getenv("TELEGRAM_STRING_SESSION")

    if not api_id or not api_hash:
        raise RuntimeError(
            "Telegram API credentials are not configured."
        )

    if session_string:
        session = StringSession(session_string)
    elif (
        os.getenv("ENABLE_LOCAL_TELEGRAM_SESSION") == "true"
        and Path("forensicvault_fyp.session").is_file()
    ):
        session = "forensicvault_fyp"
    else:
        raise RuntimeError(
            "Authorized Telegram session unavailable."
        )

    client = TelegramClient(
        session,
        int(api_id),
        api_hash,
        timeout=15,
        connection_retries=1,
        request_retries=1,
        flood_sleep_threshold=0
    )

    try:
        await client.connect()

        if not await client.is_user_authorized():
            raise RuntimeError(
                "Telegram session is not authorized."
            )

        entity = await client.get_entity(channel)

        if not isinstance(entity, Channel):
            raise ValueError(
                "Only public channels and groups are supported."
            )

        public_usernames = set()

        if entity.username:
            public_usernames.add(entity.username.lower())

        for alias in getattr(entity, "usernames", None) or []:
            if alias.active and alias.username:
                public_usernames.add(alias.username.lower())

        if not public_usernames:
            raise ValueError(
                "Private Telegram sources are not supported."
            )

        if channel.lower() not in public_usernames:
            raise ValueError(
                "Telegram source identity mismatch."
            )

        resolved_username = channel.lower()

        messages = await client.get_messages(
            entity,
            limit=10
        )

        records = []

        for message in messages:
            records.append({
                "message_id": message.id,
                "timestamp": (
                    message.date.isoformat()
                    if message.date else None
                ),
                "edited_at": (
                    message.edit_date.isoformat()
                    if message.edit_date else None
                ),
                "text": message.message or "",
                "has_media": bool(message.media),
                "source_url": (
                    f"https://t.me/{resolved_username}/{message.id}"
                )
            })

        if not records:
            raise RuntimeError(
                "No accessible Telegram messages found."
            )

        return resolved_username, records

    finally:
        await client.disconnect()


def extract_telegram_api_evidence(target_channel, case_id):

    channel = target_channel.strip().lstrip("@")

    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", channel):
        raise ValueError("Invalid Telegram username.")

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,50}", case_id):
        raise ValueError("Invalid case ID.")

    async def collect_with_timeout():
        return await asyncio.wait_for(
            collect_messages(channel),
            timeout=60
        )

    username, messages = asyncio.run(
        collect_with_timeout()
    )

    timestamp = datetime.now(timezone.utc)
    capture_id = uuid.uuid4().hex[:12]

    STORAGE_VAULT.mkdir(parents=True, exist_ok=True)

    filename = (
        f"{case_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        f"_{capture_id}_tg_api"
    )

    txt_path = STORAGE_VAULT / f"{filename}.txt"
    json_path = STORAGE_VAULT / f"{filename}.json"

    evidence = {
        "case_id": case_id,
        "platform": "Telegram",
        "source_url": f"https://t.me/{username}",
        "captured_at": timestamp.isoformat(),
        "collection_method": "Telegram API via Telethon",
        "message_count": len(messages),
        "collection_scope": "Latest 10 accessible messages",
        "media_downloaded": False,
        "messages": messages
    }

    json_path.write_text(
        json.dumps(
            evidence,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    lines = [
        "FORENSICVAULT - TELEGRAM API EVIDENCE",
        "=" * 50,
        f"Case ID: {case_id}",
        f"Source: https://t.me/{username}",
        f"Captured at: {timestamp.isoformat()}",
        "Method: Telegram API via Telethon",
        "Scope: Latest 10 accessible messages",
        "Media files are not downloaded.",
        ""
    ]

    for message in messages:
        lines.extend([
            f"Message ID: {message['message_id']}",
            f"Date: {message['timestamp']}",
            f"Edited at: {message['edited_at']}",
            f"Source: {message['source_url']}",
            f"Message: {message['text']}",
            f"Contains media: {message['has_media']}",
            "-" * 50,
            ""
        ])

    txt_path.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    return {
        "case_id": case_id,
        "target_url": f"https://t.me/{username}",
        "title": f"Telegram API: {username}",
        "artifact_paths": [
            str(txt_path),
            str(json_path)
        ],
        "extraction_date": timestamp.isoformat()
    }
