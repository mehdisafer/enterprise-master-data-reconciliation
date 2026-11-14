"""Scan byte-verified blobs from enumerated remote branch histories, never execute them."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
REPO = Path('/workspace/scratch/fc83c385ce79/enterprise-master-data-reconciliation')
started = datetime.now(timezone.utc).isoformat()
inventory = json.loads((BASE / 'remote-inventory.json').read_text())
fetched = json.loads((BASE / 'fetched-blobs.json').read_text())
messages = json.loads((BASE / 'commit-messages.json').read_text())
spec = importlib.util.spec_from_file_location('repository_secret_scan', REPO / 'scripts/secret_scan.py')
scanner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scanner
spec.loader.exec_module(scanner)
findings = []
unscanned = []
verified = []
local_count = 0
fetched_count = 0
for item in inventory['blobs']:
    oid = item['sha']
    if oid in fetched:
        content = fetched[oid].encode('utf-8')
        origin = 'connected_GitHub_blob_endpoint'
        fetched_count += 1
    else:
        content = subprocess.check_output(['git', '-C', str(REPO), 'cat-file', 'blob', oid])
        origin = 'local_git_object_matched_to_remote_tree'
        local_count += 1
    object_hash = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
    assert object_hash == oid and len(content) == item['size'], 'Remote/local object mismatch'
    for path in item['paths']:
        if scanner.secret_path(path):
            findings.append({'location': f'{oid}:{path}', 'line': 0, 'rule': 'secret-file-path'})
    if len(content) > scanner.MAX_BYTES:
        unscanned.append({'sha': oid, 'reason': 'oversized'})
        continue
    findings.extend(scanner.asdict(finding) for finding in scanner.scan('git:' + oid, content))
    if b'\0' in content:
        unscanned.append({'sha': oid, 'reason': 'binary: common-byte-patterns-only'})
    if '120000' in item['modes']:
        unscanned.append({'sha': oid, 'reason': 'symlink target; linked content not scanned'})
    verified.append({'sha': oid, 'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content), 'origin': origin})
for sha, message in messages['messages'].items():
    findings.extend(scanner.asdict(finding) for finding in scanner.scan('commit-message:' + sha, message.encode()))
if inventory['non_blob_entries']:
    unscanned.append({'reason': 'non-blob/non-tree entries present', 'entries': inventory['non_blob_entries']})
report = {
    'schema_version': 1, 'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
    'repository': inventory['repository'], 'scope': inventory['scope'], 'branches': inventory['branches'],
    'additional_refs': inventory.get('additional_refs', []),
    'reachable_commits_enumerated': len(inventory['commits']), 'recursive_trees_read': len(inventory['trees']),
    'all_trees_untruncated': all(not item['truncated'] for item in inventory['trees']),
    'unique_blobs_scanned': len(verified), 'bytes_scanned': sum(item['bytes'] for item in verified),
    'remote_blobs_fetched': fetched_count, 'matching_local_git_blobs_used': local_count,
    'git_blob_sizes_and_object_hashes_verified': len(verified), 'commit_messages_scanned': len(messages['messages']),
    'commit_identity_email_domains': messages['email_domains'],
    'scanner_sha256': hashlib.sha256((REPO / 'scripts/secret_scan.py').read_bytes()).hexdigest(),
    'findings': findings, 'unscanned_or_limited': unscanned,
    'credential_values_printed': False, 'complete_secret_detection_claimed': False,
    'tag_coverage': inventory['tag_enumeration'],
    'other_exclusions': ['unreachable Git objects', 'other repositories/forks', 'Actions annotation text and inaccessible logs', 'account secrets/settings'],
    'passed_within_stated_scope': not findings and not unscanned and len(verified) == len(inventory['blobs']),
    'verified_blobs': verified,
}
(BASE / 'remote-history-scan.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'verified_blobs'}, indent=2))
raise SystemExit(0 if report['passed_within_stated_scope'] else 1)
