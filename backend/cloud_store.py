"""Account-scoped Firestore persistence for the existing ranking services.

Transactions buffer writes until all reads complete. Events, preferences and
bookmark state commit together, so a retried event cannot apply a signal twice.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from .mock import FixtureCatalog, MockServices
from .schemas import Creator, Post, Product, UserProfile


def key(*parts: str) -> str:
    return sha256("\0".join(parts).encode()).hexdigest()


class CloudCatalog(FixtureCatalog):
    def __init__(self, client):
        for plural, model, id_field in (
            ("products", Product, "product_id"), ("posts", Post, "post_id"),
            ("creators", Creator, "creator_id"),
        ):
            values = [model.model_validate({k: v for k, v in (doc.to_dict() or {}).items()
                                          if k in model.model_fields})
                      for doc in client.collection(plural).stream()]
            setattr(self, plural, values)
            setattr(self, f"{plural}_by_id", {getattr(v, id_field): v for v in values})
        if any(p.creator_id not in self.creators_by_id for p in self.posts):
            raise ValueError("Cloud posts reference missing creators")


class CloudStore:
    def __init__(self, client, user_id: str, transaction=None):
        self.client = client
        self.user_id = user_id
        self.transaction = transaction
        self.pending = {}

    def read(self, path: str):
        if path in self.pending:
            return deepcopy(self.pending[path])
        doc = self.client.document(path).get(transaction=self.transaction)
        return doc.to_dict() if doc.exists else None

    def write(self, path: str, data: dict):
        if self.transaction is not None:
            self.pending[path] = deepcopy(data)
        else:
            self.client.document(path).set(data, merge=True)

    def atomic(self, operation):
        @firestore.transactional
        def execute(transaction):
            scoped = CloudStore(self.client, self.user_id, transaction)
            result = operation(scoped)
            for path, data in scoped.pending.items():
                transaction.set(self.client.document(path), data, merge=True)
            return result
        return execute(self.client.transaction())

    def event_path(self, event_id):
        return f"interactions/{key(self.user_id, event_id)}"

    def has_event_id(self, event_id):
        return self.read(self.event_path(event_id)) is not None

    def insert_event(self, event):
        if event["user_id"] != self.user_id:
            raise ValueError("Event account mismatch")
        if self.has_event_id(event["event_id"]):
            return False
        self.write(self.event_path(event["event_id"]), event)
        session_path = self.session_path(event["session_id"])
        session = self.read(session_path) or {}
        self.write(session_path, {**session, "user_id": self.user_id,
                                 "session_id": event["session_id"], "updated_at": event["created_at"]})
        if event.get("target_type") == "post":
            path = f"users/{self.user_id}/post_states/{key(event['target_id'])}"
            state = self.read(path) or {"post_id": event["target_id"]}
            kind = event["event_type"]
            if kind == "impression" and event.get("is_foreground", True):
                state.update(seen=True, last_seen_at=event["created_at"])
            if kind in {"like", "unlike", "save", "unsave"}:
                field = "liked" if kind in {"like", "unlike"} else "saved"
                state[field] = kind in {"like", "save"}
            self.write(path, state)
        return True

    def get_user_profile(self, user_id):
        if user_id != self.user_id:
            raise ValueError("Profile account mismatch")
        data = self.read(f"users/{user_id}") or {"user_id": user_id}
        profile = {k: v for k, v in data.items() if k in UserProfile.model_fields}
        weights = dict(profile.get("preference_weights", {}))
        for style in profile.get("preferred_styles", []):
            weights.setdefault(f"style:{style}", 0.4)
        profile["preference_weights"] = weights
        return profile

    def save_user_profile(self, user_id, profile):
        if user_id != self.user_id:
            raise ValueError("Profile account mismatch")
        self.write(f"users/{user_id}", profile)

    def session_path(self, session_id):
        return f"sessions/{key(self.user_id, session_id)}"

    def get_profile(self, session_id):
        return self.get_user_profile(self.user_id)

    def save_profile(self, session_id, user_id, profile):
        self.save_user_profile(user_id, profile)

    def get_intent(self, session_id):
        return (self.read(self.session_path(session_id)) or {}).get("intent")

    def save_intent(self, session_id, user_id, intent):
        if user_id != self.user_id:
            raise ValueError("Session account mismatch")
        self.write(self.session_path(session_id), {"user_id": user_id,
                   "session_id": session_id, "intent": intent})

    def list_user_events(self, user_id, limit=None):
        if user_id != self.user_id:
            raise ValueError("Event account mismatch")
        query = self.client.collection("interactions").where(filter=FieldFilter("user_id", "==", user_id))
        events = {doc.id: doc.to_dict() for doc in query.stream(transaction=self.transaction)}
        events.update({path.split("/")[-1]: data for path, data in self.pending.items()
                       if path.startswith("interactions/")})
        return list(events.values())

    def has_qualifying_dwell(self, session_id, target_type, target_id):
        path = f"users/{self.user_id}/dwell_states/{key(session_id, target_type, target_id)}"
        return bool(self.read(path))

    def mark_dwell(self, event):
        path = f"users/{self.user_id}/dwell_states/{key(event.session_id, event.target_type, event.target_id)}"
        self.write(path, {"qualified": True})

    def trend_scores(self):
        return (self.read("system/trends") or {}).get("scores", {})


class CloudServices(MockServices):
    def record_interactions(self, events):
        from .schemas import EventBatchResult
        def apply(store):
            service = MockServices(self.catalog, store)
            accepted = duplicates = 0
            for event in events:
                result = service.record_interactions([event])
                accepted += result.accepted_count
                duplicates += result.duplicate_count
                if (result.accepted_count and event.event_type == "dwell"
                        and event.is_foreground and (event.dwell_ms or 0) >= 2000):
                    store.mark_dwell(event)
            return EventBatchResult(accepted_count=accepted, duplicate_count=duplicates)
        return self.store.atomic(apply)

    def feedback(self, event):
        return self.store.atomic(lambda store: MockServices(self.catalog, store).feedback(event))
