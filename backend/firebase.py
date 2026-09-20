"""Firebase Admin entrypoint for Google Cloud and local ADC environments."""

from __future__ import annotations

from functools import lru_cache
import os

import firebase_admin
from firebase_admin import firestore


@lru_cache(maxsize=1)
def initialize_firebase() -> firebase_admin.App:
    """Initialize Firebase Admin using Application Default Credentials."""
    if firebase_admin._apps:
        return firebase_admin.get_app()
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
    options = {"projectId": project} if project else {}
    bucket = os.getenv("FIREBASE_STORAGE_BUCKET")
    if bucket:
        options["storageBucket"] = bucket
    return firebase_admin.initialize_app(options=options)


@lru_cache(maxsize=1)
def get_firestore_client() -> firestore.Client:
    initialize_firebase()
    return firestore.client()
