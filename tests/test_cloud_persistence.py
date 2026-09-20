"""Offline contract tests; real Firebase acceptance is a separate script."""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.cloud_api import create_cloud_app
from backend.cloud_store import key
from backend.config import ROOT, Settings
from backend.mock import FixtureCatalog


class Snapshot:
    def __init__(self, path, value):
        self.id = path.split('/')[-1]
        self.value = deepcopy(value)
        self.exists = value is not None

    def to_dict(self):
        return deepcopy(self.value)


class Reference:
    def __init__(self, db, path):
        self.db, self.path = db, path

    def get(self, transaction=None, **kwargs):
        if transaction and transaction.writes:
            raise RuntimeError('Firestore reads must precede writes')
        return Snapshot(self.path, self.db.data.get(self.path))

    def set(self, value, merge=False):
        self.db.data[self.path] = {**(self.db.data.get(self.path, {}) if merge else {}), **deepcopy(value)}

    def delete(self):
        self.db.data.pop(self.path, None)


class Collection:
    def __init__(self, db, path, filter=None):
        self.db, self.path, self.filter = db, path, filter

    def document(self, name):
        return Reference(self.db, self.path + '/' + name)

    def where(self, *, filter):
        return Collection(self.db, self.path, filter)

    def stream(self, transaction=None):
        if transaction and transaction.writes:
            raise RuntimeError('Firestore reads must precede writes')
        for path, data in list(self.db.data.items()):
            if path.rsplit('/', 1)[0] == self.path:
                if self.filter is None or data.get(self.filter.field_path) == self.filter.value:
                    yield Snapshot(path, data)


class Transaction:
    def __init__(self, db):
        self.db, self.writes = db, []

    def set(self, ref, data, merge=False):
        self.writes.append((ref, data, merge))

    def commit(self):
        if self.db.fail_commit:
            self.db.fail_commit = False
            raise RuntimeError('Simulated commit outage')
        for ref, data, merge in self.writes:
            ref.set(data, merge)


class MemoryFirestore:
    project = 'offline-test'

    def __init__(self):
        self.data = {}
        self.fail_commit = False

    def document(self, path):
        return Reference(self, path)

    def collection(self, path):
        return Collection(self, path)

    def transaction(self):
        return Transaction(self)

    def batch(self):
        return Transaction(self)


@pytest.fixture
def cloud(monkeypatch, tmp_path):
    db = MemoryFirestore()
    catalog = FixtureCatalog(ROOT / 'data/fixtures')
    for collection, items, id_field in (
        ('posts', catalog.posts, 'post_id'), ('products', catalog.products, 'product_id'),
        ('creators', catalog.creators, 'creator_id'),
    ):
        for item in items:
            db.data[f'{collection}/{getattr(item, id_field)}'] = item.model_dump(mode='json')
    monkeypatch.setattr('backend.cloud_api.get_firestore_client', lambda: db)
    monkeypatch.setattr('backend.cloud_api.initialize_firebase', lambda: SimpleNamespace(project_id=db.project))
    monkeypatch.setattr('firebase_admin.auth.verify_id_token', lambda token: {'uid': token})

    def transactional(function):
        def run(transaction):
            result = function(transaction)
            transaction.commit()
            return result
        return run
    monkeypatch.setattr('backend.cloud_store.firestore.transactional', transactional)
    settings = Settings('mock', ('http://localhost:5173',), tmp_path/'unused.sqlite3', ROOT/'data/fixtures', 8, ('admin',), 'firestore')
    return TestClient(create_cloud_app(settings), raise_server_exceptions=False), db, catalog.posts[0].post_id


def headers(uid='a'):
    return {'Authorization': f'Bearer {uid}'}


def test_cloud_authorization_and_onboarding(cloud):
    client, db, _ = cloud
    assert client.get('/api/v1/me').status_code == 401
    assert client.get('/api/v1/admin/status', headers=headers()).json() == {'is_admin': False}
    assert client.get('/api/v1/admin/status', headers=headers('admin')).json() == {'is_admin': True}
    assert client.get('/api/v1/admin/insights', headers=headers()).status_code == 403
    assert client.get('/api/v1/profile/b', headers=headers()).status_code == 403
    result = client.put('/api/v1/me/onboarding', headers=headers(), json={'age_range': '25-34', 'preferred_styles': ['minimal']})
    assert result.status_code == 200
    assert db.data['users/a']['onboarding_completed'] is True
    assert client.get('/api/v1/profile/a', headers=headers()).json()['preference_weights']['style:minimal'] == .4
    assert client.get('/api/v1/me', headers=headers('b')).json()['profile'] is None


def test_event_and_preference_commit_retry_are_atomic(cloud):
    client, db, post_id = cloud
    body = {'event_id': 'same-event', 'session_id': 'same-session', 'user_id': 'forged',
            'event_type': 'like', 'target_type': 'post', 'target_id': post_id}
    db.fail_commit = True
    assert client.post('/api/v1/events/batch', headers=headers(), json=[body]).status_code == 503
    assert not any(path.startswith('interactions/') for path in db.data)
    assert 'users/a' not in db.data
    assert client.post('/api/v1/events/batch', headers=headers(), json=[body]).json()['accepted_count'] == 1
    version = db.data['users/a']['profile_version']
    assert client.post('/api/v1/events/batch', headers=headers(), json=[body]).json()['duplicate_count'] == 1
    assert db.data['users/a']['profile_version'] == version
    assert client.post('/api/v1/events/batch', headers=headers('b'), json=[body]).json()['accepted_count'] == 1
    assert db.data[f'interactions/{key("a", "same-event")}']['user_id'] == 'a'
    assert db.data[f'interactions/{key("b", "same-event")}']['user_id'] == 'b'


def test_bookmarks_restore_outside_feed_and_can_be_removed(cloud):
    client, db, post_id = cloud
    state = {'event_id': 'save', 'session_id': 's', 'field': 'saved', 'value': True}
    url = f'/api/v1/me/posts/{post_id}/state'
    assert client.put(url, headers=headers(), json=state).status_code == 200
    assert client.get('/api/v1/me', headers=headers()).json()['saved_ids'] == [post_id]
    assert client.get('/api/v1/me/posts?kind=saved', headers=headers()).json()['items'][0]['post']['post_id'] == post_id
    assert client.get('/api/v1/me/posts?kind=saved', headers=headers('b')).json()['items'] == []
    state.update(event_id='unsave', value=False)
    assert client.put(url, headers=headers(), json=state).status_code == 200
    assert client.get('/api/v1/me', headers=headers()).json()['saved_ids'] == []
    assert db.data[f'interactions/{key("a", "unsave")}']['event_type'] == 'unsave'


def test_seen_posts_and_sessions_are_account_scoped(cloud):
    client, db, post_id = cloud
    event = {'event_id': 'view', 'session_id': 'same', 'event_type': 'impression', 'target_type': 'post', 'target_id': post_id}
    assert client.post('/api/v1/events/batch', headers=headers(), json=[event]).status_code == 200
    feed = client.get('/api/v1/feed?session_id=new', headers=headers())
    assert feed.status_code == 200, feed.text
    assert post_id not in [p['post_id'] for p in feed.json()['items']]
    db.data[f'sessions/{key("b", "same")}'] = {'user_id': 'b', 'intent': {'session_id': 'same'}}
    assert client.post('/api/v1/session/same/reset', headers=headers()).status_code == 200
    assert f'sessions/{key("b", "same")}' in db.data
    assert f'interactions/{key("a", "view")}' in db.data


def test_foreground_dwell_only_once_per_session(cloud):
    client, db, post_id = cloud
    event = {'event_id': 'dwell1', 'session_id': 's', 'event_type': 'dwell', 'target_type': 'post', 'target_id': post_id, 'dwell_ms': 8500}
    assert client.post('/api/v1/events/batch', headers=headers(), json=[event]).status_code == 200
    version = db.data['users/a']['profile_version']
    event['event_id'] = 'dwell2'
    assert client.post('/api/v1/events/batch', headers=headers(), json=[event]).status_code == 200
    assert db.data['users/a']['profile_version'] == version
