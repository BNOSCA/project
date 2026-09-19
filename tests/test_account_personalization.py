from pathlib import Path

from backend.db import EventStore
from backend.mock import FixtureCatalog, MockServices
from backend.schemas import FeedbackEvent, InteractionEvent


def test_long_term_preferences_are_isolated_by_account(tmp_path: Path):
    services = MockServices(
        FixtureCatalog(Path("data/catalog/combined")),
        EventStore(tmp_path / "demo.sqlite3"),
    )
    post = services.catalog.posts[0]

    profile_a, duplicate = services.feedback(FeedbackEvent(
        event_id="account-a-like",
        session_id="session-a",
        user_id="account-a",
        event_type="like",
        target_type="post",
        target_id=post.post_id,
    ))

    assert not duplicate
    assert profile_a.preference_weights
    assert services.store.get_user_profile("account-a")
    assert services.store.get_user_profile("account-b") is None

    feed_a = services.feed("account-a", "new-session-a", None, 5)
    feed_b = services.feed("account-b", "session-b", None, 5)
    assert feed_a.profile_version == 1
    assert feed_b.profile_version == 0


def test_impressions_hide_posts_only_for_the_same_account_across_sessions(tmp_path: Path):
    services = MockServices(
        FixtureCatalog(Path("data/catalog/combined")),
        EventStore(tmp_path / "demo.sqlite3"),
    )
    first = services.feed("account-a", "session-a", None, 3)
    seen_ids = [item.post_id for item in first.items]
    services.record_interactions([
        InteractionEvent(
            event_id=f"seen-{index}",
            session_id="session-a",
            user_id="account-a",
            event_type="impression",
            target_type="post",
            target_id=post_id,
            position=index,
        )
        for index, post_id in enumerate(seen_ids)
    ])

    refreshed_a = services.feed("account-a", "session-a-next", None, 20)
    first_b = services.feed("account-b", "session-b", None, 3)

    assert set(seen_ids).isdisjoint(item.post_id for item in refreshed_a.items)
    assert [item.post_id for item in first_b.items] == seen_ids
