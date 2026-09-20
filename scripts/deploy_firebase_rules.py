"""Deploy versioned rules with existing service-account permissions only.

Uses the documented Firebase Rules REST API. Never modifies IAM or billing.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.config import Settings
import google.auth
from google.auth.transport.requests import AuthorizedSession


def deploy(apply=False):
    Settings.from_env()
    project = os.environ['GOOGLE_CLOUD_PROJECT']
    if project != 'bnosca-outfit-demo':
        raise ValueError('Unexpected Firebase project')
    credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    session = AuthorizedSession(credentials)
    base = f'https://firebaserules.googleapis.com/v1/projects/{project}'
    report = {}
    for file_name, release_id in (
        ('firestore.rules', 'cloud.firestore'),
        ('storage.rules', 'firebase.storage/' + os.environ['FIREBASE_STORAGE_BUCKET']),
    ):
        release_url = f'{base}/releases/{release_id}'
        current = session.get(release_url, timeout=15)
        entry = {'current_release_http': current.status_code}
        report[file_name] = entry
        if current.status_code not in (200, 404):
            entry['error'] = current.json().get('error', {}).get('message', 'Access denied')
            continue
        if not apply:
            continue
        if current.status_code == 200:
            entry['previous_ruleset'] = current.json().get('rulesetName')
        result = session.post(f'{base}/rulesets', json={'source': {'files': [
            {'name': file_name, 'content': (ROOT/'firebase'/file_name).read_text(encoding='utf-8')}
        ]}}, timeout=15)
        entry['compile_http'] = result.status_code
        if result.status_code != 200:
            entry['error'] = result.json().get('error', {}).get('message', 'Rules validation failed')
            continue
        ruleset = result.json()['name']
        release = {'name': f'projects/{project}/releases/{release_id}', 'rulesetName': ruleset}
        if current.status_code == 200:
            result = session.patch(release_url, json={'release': release, 'updateMask': 'rulesetName'}, timeout=15)
        else:
            result = session.post(f'{base}/releases', json=release, timeout=15)
        entry.update(deploy_http=result.status_code, ruleset=ruleset)
        if result.status_code != 200:
            entry['error'] = result.json().get('error', {}).get('message', 'Release failed')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    print(json.dumps(deploy(parser.parse_args().apply), ensure_ascii=True, indent=2))
