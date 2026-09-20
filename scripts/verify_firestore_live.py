"""Live acceptance against real Firebase with a disposable account.

Uses a temporary Auth account and removes only its own test artifacts in finally.
Never logs service-account credentials, ID tokens or refresh tokens.
"""
from __future__ import annotations

import base64
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
from urllib.parse import quote
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests
from fastapi.testclient import TestClient
from firebase_admin import auth, storage
from google.cloud.firestore_v1.base_query import FieldFilter

from backend.config import Settings, load_dotenv
from backend.cloud_api import create_cloud_app
from backend.cloud_store import key
from backend.firebase import get_firestore_client, initialize_firebase


def verify():
    settings = replace(Settings.from_env(), storage_backend='firestore')
    initialize_firebase()
    db = get_firestore_client()
    if db.project != 'bnosca-outfit-demo':
        raise ValueError('Unexpected Firebase project')
    load_dotenv(ROOT/'frontend/.env.local')
    api_key = os.environ['VITE_FIREBASE_API_KEY']

    def token(uid):
        custom = auth.create_custom_token(uid).decode()
        response = requests.post('https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken',
            params={'key': api_key}, json={'token': custom, 'returnSecureToken': True}, timeout=20)
        if response.status_code != 200:
            raise RuntimeError(f'Firebase token exchange failed: HTTP {response.status_code}')
        return response.json()['idToken']

    uid = 'cloud-acceptance-' + uuid.uuid4().hex
    session = 'acceptance-' + uuid.uuid4().hex
    own_post = 'post-user-' + str(uuid.uuid4())
    report = {'project': db.project}
    created_user = False
    uploaded = False
    try:
        auth.create_user(uid=uid, display_name='Temporary acceptance account')
        created_user = True
        id_token = token(uid)
        headers = {'Authorization': 'Bearer ' + id_token}
        client = TestClient(create_cloud_app(settings), raise_server_exceptions=False)
        assert client.get('/health').status_code == 200
        assert client.get('/api/v1/admin/status', headers=headers).json() == {'is_admin': False}
        assert client.get('/api/v1/admin/insights', headers=headers).status_code == 403
        assert client.get('/api/v1/me').status_code == 401
        assert client.get('/api/v1/profile/someone-else', headers=headers).status_code == 403
        report['regular_access'] = 'passed'
        account = client.get('/api/v1/me', headers=headers).json()
        assert account['profile'] is None
        response = client.put('/api/v1/me/onboarding', headers=headers,
            json={'age_range': '25-34', 'preferred_styles': ['japanese', 'minimal']})
        assert response.status_code == 200, response.text
        response = client.put('/api/v1/me/public-profile', headers=headers,
            json={'displayName': 'Acceptance', 'username': 'acceptance', 'bio': 'Temporary test'})
        assert response.status_code == 200, response.text
        assert client.get('/api/v1/me', headers=headers).json()['profile']['onboarding_completed']
        report['onboarding_and_profile'] = 'passed'
        feed = client.get('/api/v1/feed', params={'session_id': session}, headers=headers)
        assert feed.status_code == 200, feed.text
        post_id = feed.json()['items'][0]['post_id']
        body = [{'event_id': 'view1', 'session_id': session, 'event_type': 'impression',
                 'user_id': 'forged', 'target_type': 'post', 'target_id': post_id}]
        assert client.post('/api/v1/events/batch', headers=headers, json=body).json()['accepted_count'] == 1
        assert client.post('/api/v1/events/batch', headers=headers, json=body).json()['duplicate_count'] == 1
        for field in ('liked', 'saved'):
            result = client.put(f'/api/v1/me/posts/{post_id}/state', headers=headers,
                json={'event_id': field, 'session_id': session, 'field': field, 'value': True})
            assert result.status_code == 200, result.text
        response = client.get('/api/v1/me/posts?kind=saved', headers=headers)
        assert post_id in [item['post']['post_id'] for item in response.json()['items']]
        result = client.put(f'/api/v1/me/posts/{post_id}/state', headers=headers,
            json={'event_id': 'unsave', 'session_id': session, 'field': 'saved', 'value': False})
        assert result.status_code == 200, result.text
        assert client.get('/api/v1/me', headers=headers).json()['saved_ids'] == []
        # A new app instance reads the same cloud profile and excludes seen posts.
        restarted = TestClient(create_cloud_app(settings), raise_server_exceptions=False)
        after = restarted.get('/api/v1/feed', params={'session_id': 'new-session'}, headers=headers)
        assert post_id not in [item['post_id'] for item in after.json()['items']]
        assert restarted.get('/api/v1/profile/'+uid, headers=headers).json()['profile_version'] >= 3
        report['events_bookmarks_restart_seen'] = 'passed'
        search = client.post('/api/v1/search', headers=headers, json={'session_id': session,
            'mode': 'text', 'query_text': '日系', 'filters': {}})
        assert search.status_code == 200, search.text
        assert list(db.collection('search_history').where(filter=FieldFilter('user_id','==',uid)).stream())
        report['search_history'] = 'passed'
        # Validate the real test1 token without modifying test1's profile or behavior.
        test1 = 'bbEJojA0sNTF4vfvN8fhLBM79dC3'
        admin_headers = {'Authorization': 'Bearer '+token(test1)}
        assert client.get('/api/v1/admin/status', headers=admin_headers).json() == {'is_admin': True}
        insights = client.get('/api/v1/admin/insights', headers=admin_headers)
        assert insights.status_code == 200, insights.text
        report['test1_admin'] = 'passed'

        bucket = os.environ['FIREBASE_STORAGE_BUCKET']
        image_path = f'uploads/{uid}/{own_post}'
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jLfkAAAAASUVORK5CYII=')
        upload = requests.post(f'https://firebasestorage.googleapis.com/v0/b/{bucket}/o',
            params={'name': image_path, 'uploadType': 'media'}, data=png,
            headers={**headers, 'Content-Type': 'image/png'}, timeout=20)
        report['storage_upload_http'] = upload.status_code
        if upload.status_code == 200:
            uploaded = True
            published = client.post('/api/v1/me/posts', headers=headers,
                json={'post_id': own_post, 'caption': 'Temporary acceptance test', 'image_path': image_path})
            assert published.status_code == 200, published.text
            assert own_post in [x['post']['post_id'] for x in client.get('/api/v1/me/posts?kind=own', headers=headers).json()['items']]
            repeated = client.post('/api/v1/me/posts', headers=headers,
                json={'post_id': own_post, 'caption': 'Temporary acceptance test', 'image_path': image_path})
            assert repeated.status_code == 200
            report['publish'] = 'passed'
        else:
            report['publish'] = 'blocked by Storage configuration/rules'
        return report
    finally:
        if created_user:
            for name in ('interactions','sessions','search_history','recommendation_runs'):
                for doc in db.collection(name).where(filter=FieldFilter('user_id','==',uid)).stream():
                    doc.reference.delete()
            user_ref = db.document('users/'+uid)
            for collection in user_ref.collections():
                for doc in collection.stream():
                    doc.reference.delete()
            user_ref.delete()
            db.document('creators/'+uid).delete()
            db.document('posts/'+own_post).delete()
            if uploaded:
                storage.bucket().blob(f'uploads/{uid}/{own_post}').delete()
            auth.delete_user(uid)
            report['temporary_account_cleanup'] = 'complete'


if __name__ == '__main__':
    print(json.dumps(verify(), ensure_ascii=True, indent=2))
