"""Firebase Admin entrypoint for Google Cloud and local ADC environments."""

from __future__ import annotations

from functools import lru_cache

import firebase_admin
from firebase_admin import firestore


@lru_cache(maxsize=1)
def initialize_firebase() -> firebase_admin.App:
    """Initialize Firebase Admin using Application Default Credentials."""
    if firebase_admin._apps:
        return firebase_admin.get_app()
    return firebase_admin.initialize_app()


@lru_cache(maxsize=1)
def get_firestore_client() -> firestore.Client:
    initialize_firebase()
    return firestore.client()
