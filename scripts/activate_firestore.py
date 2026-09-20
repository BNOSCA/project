"""Import configured catalog and local account history without deleting SQLite.

Dry-run is the default. --apply creates missing cloud documents; it never
overwrites an existing catalog document or existing account preference field.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from google.api_core.exceptions import AlreadyExists
from backend.config import Settings
from backend.cloud_store import CloudStore, key
from backend.firebase import get_firestore_client
from backend.mock import FixtureCatalog


def migrate(apply=False):
    settings = Settings.from_env()
    catalog = FixtureCatalog(settings.data_dir)
    report = {"apply": apply, "catalog_source": str(settings.data_dir),
              "catalog": {name: len(getattr(catalog, name)) for name in ("products", "posts", "creators")}}
    db = sqlite3.connect(settings.db_path.resolve().as_uri() + "?mode=ro", uri=True)
    profiles = {uid: json.loads(data) for uid, data in db.execute("SELECT user_id,profile_json FROM user_profiles")}
    events = [json.loads(data) for (data,) in db.execute("SELECT payload FROM events ORDER BY created_at,event_id")]
    sessions = [(sid, uid, json.loads(data)) for sid, uid, data in db.execute(
        "SELECT session_id,user_id,intent_json FROM session_profiles WHERE intent_json IS NOT NULL")]
    db.close()
    users = (set(profiles) | {e["user_id"] for e in events} | {uid for _, uid, _ in sessions}) - {"anonymous-demo"}
    report.update(accounts=len(users), events=len(events), anonymous_skipped=sum(e["user_id"] == "anonymous-demo" for e in events))
    if not apply:
        return report
    from firebase_admin import auth
    client = get_firestore_client()
    if client.project != "bnosca-outfit-demo":
        raise ValueError("Refusing to import into a different project")
    created = {}
    for name, id_field in (("creators", "creator_id"), ("products", "product_id"), ("posts", "post_id")):
        created[name] = 0
        for item in getattr(catalog, name):
            data = item.model_dump(mode="json")
            try:
                client.collection(name).document(data[id_field]).create(data)
                created[name] += 1
            except AlreadyExists:
                pass
    migrated = 0
    for uid in users:
        auth.get_user(uid)  # Only import records for real Firebase accounts.
        user_events = [e for e in events if e["user_id"] == uid]
        if len(user_events) > 150:
            raise ValueError("Large historical import requires batched migration; SQLite unchanged")
        def import_account(store):
            marker = f"users/{uid}/migrations/sqlite-v1"
            if store.read(marker):
                return False
            current = store.read(f"users/{uid}") or {}
            local = profiles.get(uid, {"user_id": uid})
            store.write(f"users/{uid}", {**local, **current, "user_id": uid})
            states = {}
            for event in user_events:
                path = store.event_path(event["event_id"])
                if not store.read(path):
                    # Preserve original timestamps. Old missing dates are unknown, not 'now'.
                    store.write(path, event)
                if event.get("target_type") == "post":
                    post_id = event["target_id"]
                    state = states.setdefault(post_id, {"post_id": post_id})
                    kind = event["event_type"]
                    if kind == "impression" and event.get("is_foreground", True):
                        state.update(seen=True, last_seen_at=event.get("created_at"))
                    if kind in {"like", "save", "unlike", "unsave"}:
                        state["liked" if kind in {"like", "unlike"} else "saved"] = kind in {"like", "save"}
                session_path = store.session_path(event["session_id"])
                if not store.read(session_path):
                    store.write(session_path, {"user_id": uid, "session_id": event["session_id"]})
            for post_id, state in states.items():
                path = f"users/{uid}/post_states/{key(post_id)}"
                if not store.read(path):
                    store.write(path, state)
            for sid, session_uid, intent in sessions:
                if session_uid == uid and not store.get_intent(sid):
                    store.save_intent(sid, uid, intent)
            store.write(marker, {"completed_at": datetime.now(timezone.utc), "events": len(user_events)})
            return True
        migrated += int(CloudStore(client, uid).atomic(import_account))
    report.update(created=created, migrated_accounts=migrated)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(migrate(args.apply), ensure_ascii=True, indent=2))
