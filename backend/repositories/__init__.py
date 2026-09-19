"""Firestore repository layer.

Application code should depend on these repositories instead of importing the
Firestore SDK directly. The current demo runtime still uses fixtures by default.
"""

from .creators import CreatorRepository
from .interactions import InteractionRepository
from .posts import PostRepository
from .products import ProductRepository
from .sessions import SessionRepository
from .users import UserRepository

__all__ = [
    "CreatorRepository",
    "InteractionRepository",
    "PostRepository",
    "ProductRepository",
    "SessionRepository",
    "UserRepository",
]
