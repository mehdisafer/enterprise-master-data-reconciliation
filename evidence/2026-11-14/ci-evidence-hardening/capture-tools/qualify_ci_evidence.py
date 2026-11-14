"""Exercise selected, unchanged workflow steps against the isolated native PG runtime.

No empty-target restore or database reset is performed. The populated synthetic
databases and the previously qualified archive are checked before the negative
case. Separate, fresh work directories retain all outputs and failure controls.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import psycopg
from psycopg import sql
import yaml


REPO = Path('/workspace/scratch/fc83c385ce79/enterprise-master-data-reconciliation')
BASE = Path(__file__).resolve().parent
PREVIOUS = Path('/workspace/scratch/fc83c385ce79/p02-postgres-runtime/qualification/20261114T121255604194Z')
TABLES = (
    'raw_records', 'source_records', 'identity_groups', 'memberships',
    'golden_history', 'decisions', 'outbox', 'consumer_inbox', 'consumer_records',
    'schema_migrations', 'standard_records', 'membership_history', 'candidates',
    'decision_events', 'consumer_crosswalk', 'runs', 'run_sources',
)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def fingerprint(dsn, database):
    result = {}
    with psycopg.connect(dsn, connect_timeout=5) as connection:
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        connection.execute("SET TIME ZONE 'UTC'")
        connection.execute("SET statement_timeout = '30s'")
        assert connection.execute('SELECT current_database()').fetchone()[0] == database
        for table in TABLES:
            query = sql.SQL('SELECT to_jsonb(t)::text FROM {} t ORDER BY to_jsonb(t)::text').format(
                sql.Identifier('public', table)
            )
            digest = hashlib.sha256()
            rows = 0
            for (row,) in connection.execute(query):
                digest.update(row.encode() + b'\n')
                rows += 1
            result[table] = {'rows': rows, 'sha256': digest.hexdigest()}
        assert result['source_records']['rows'] == 34, 'Expected synthetic reference only'
    return result


def prepare(directory, archive=True):
    directory.mkdir(parents=True)
    for name in ('pyproject.toml', 'uv.lock', 'README.md'):
        shutil.copy2(REPO / name, directory / name)
    (directory / '.venv').symlink_to(REPO / '.venv', target_is_directory=True)
    (directory / 'scripts').mkdir()
    shutil.copy2(REPO / 'scripts/restore.sh', directory / 'scripts/restore.sh')
    shutil.copytree(REPO / 'dbt', directory / 'dbt', ignore=shutil.ignore_patterns('target', 'logs', 'dbt_packages'))
    (directory / 'artifacts').mkdir()
    if archive:
        for name in ('reference.dump', 'reference.dump.manifest.json'):
            shutil.copy2(PREVIOUS / name, directory / 'artifacts' / name)


def main():
    os.umask(0o077)
    started = now()
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directory = BASE / 'runs' / run_id
    directory.mkdir(parents=True)
    workflow_file = REPO / '.github/workflows/quality.yml'
    workflow = yaml.safe_load(workflow_file.read_text())
    steps = {step.get('name'): step for step in workflow['jobs']['postgres']['steps']}
    dbt_script = steps['Execute dbt models, contracts and data tests']['run']
    restore_script = steps['Reject a second restore into the populated database']['run']
    inputs = [workflow_file, REPO / 'scripts/restore.sh', REPO / 'pyproject.toml', REPO / 'uv.lock']
    inputs += [path for path in (REPO / 'dbt').rglob('*') if path.is_file() and not any(
        item in {'target', 'logs', 'dbt_packages'} for item in path.relative_to(REPO / 'dbt').parts
    )]
    input_hashes = {str(path.relative_to(REPO)): sha(path) for path in sorted(inputs)}
    write_json(directory / 'source-before.json', input_hashes)
    environment = os.environ.copy()
    environment.update({'UV_OFFLINE': 'true', 'DBT_SEND_ANONYMOUS_USAGE_STATS': 'false', 'DO_NOT_TRACK': '1'})
    archive = PREVIOUS / 'reference.dump'
    manifest = json.loads((PREVIOUS / 'reference.dump.manifest.json').read_text())
    assert sha(archive) == manifest['archive_sha256'], 'Archive differs from its preserved manifest'
    targets = {'mdm': environment['MDM_DATABASE_URL'], 'mdm_restore': environment['MDM_RESTORE_DATABASE_URL']}
    before = {name: fingerprint(dsn, name) for name, dsn in targets.items()}
    assert before['mdm_restore'] == manifest['tables'], 'Populated target no longer matches the prior restored fixture'
    write_json(directory / 'database-before.json', before)
    records = []
    report = {
        'started_at': started, 'passed': False,
        'scope': 'selected_workflow_commands_on_native_PostgreSQL_not_GitHub_or_Docker',
        'workflow_sha256': sha(workflow_file), 'input_file_count': len(inputs),
        'archive_sha256': sha(archive), 'archive_bytes': archive.stat().st_size,
        'restore_positive_case_reexecuted': False, 'databases_reset': False,
        'commands': records,
        'runtime_difference': 'Native PG 17.12 clients and private passfile replace CI service-container clients; uv uses the same frozen installed project environment.',
    }

    def execute(name, body, work, expected=0, overrides=None, remove=()):
        command_dir = directory / 'commands' / name
        command_dir.mkdir(parents=True)
        script = command_dir / 'step.sh'
        script.write_text(body)
        call_environment = environment.copy()
        call_environment.update(overrides or {})
        for key in remove:
            call_environment.pop(key, None)
        call_started = now()
        mark = time.monotonic()
        with (command_dir / 'stdout.txt').open('wb') as stdout, (command_dir / 'stderr.txt').open('wb') as stderr:
            result = subprocess.run(['bash', '-euo', 'pipefail', str(script)], cwd=work, env=call_environment,
                                    stdout=stdout, stderr=stderr, check=False, timeout=180)
        record = {'name': name, 'started_at': call_started, 'finished_at': now(),
                  'elapsed_seconds': round(time.monotonic() - mark, 6), 'returncode': result.returncode,
                  'expected_returncode': expected, 'script_sha256': sha(script), 'working_directory': str(work)}
        records.append(record)
        write_json(command_dir / 'execution.json', record)
        print(json.dumps(record), flush=True)
        assert result.returncode == expected, f'{name}: unexpected exit, inspect retained outputs'

    try:
        reference = directory / 'reference-work'
        prepare(reference)
        dbt_lines = [line for line in dbt_script.splitlines() if line.strip()]
        assert len(dbt_lines) == 3 and ' dbt build ' in dbt_lines[1] and ' dbt docs generate ' in dbt_lines[2]
        execute('01-dbt-deps', dbt_lines[0] + '\n', reference)
        execute('02-dbt-build', dbt_lines[1] + '\n', reference)
        build_dir = reference / 'artifacts/dbt-build'
        build_hashes = {name: sha(build_dir / name) for name in ('manifest.json', 'run_results.json')}
        execute('03-dbt-docs', dbt_lines[2] + '\n', reference)
        assert build_hashes == {name: sha(build_dir / name) for name in build_hashes}, 'Docs overwrote build results'
        build = json.loads((build_dir / 'run_results.json').read_text())
        docs = json.loads((reference / 'artifacts/dbt-docs/run_results.json').read_text())
        catalog = json.loads((reference / 'artifacts/dbt-docs/catalog.json').read_text())
        assert build['args']['which'] == 'build' and docs['args']['which'] == 'generate'
        assert build['metadata']['invocation_id'] != docs['metadata']['invocation_id']
        assert Counter(result['status'] for result in build['results']) == {'pass': 41, 'success': 7}
        assert len(catalog['nodes']) == 5 and len(catalog['sources']) == 16 and not catalog.get('errors')
        report['dbt'] = {'build_unchanged_after_docs': True, 'build_artifact_sha256': build_hashes,
                         'build_status_counts': dict(Counter(item['status'] for item in build['results'])),
                         'docs_status_counts': dict(Counter(item['status'] for item in docs['results'])),
                         'build_invocation_id': build['metadata']['invocation_id'],
                         'docs_invocation_id': docs['metadata']['invocation_id'],
                         'catalog_models': len(catalog['nodes']), 'catalog_sources': len(catalog['sources'])}
        execute('04-expected-populated-target', restore_script, reference)
        rejection = json.loads((reference / 'artifacts/second-restore-rejection.json').read_text())
        assert rejection['passed'] and all(rejection['checks'].values())
        report['populated_target_control'] = {'workflow_exit': 0, 'restore_exit': rejection['returncode'],
                                            'expected_reason': rejection['response']['reason']}
        controls = []
        for name, archive_present, remove, reason in (
            ('05-missing-archive', False, (), 'Archive must be a regular file'),
            ('06-missing-restore-configuration', True,
             ('MDM_RESTORE_DATABASE_URL', 'MDM_RESTORE_DATABASE_URL_FILE'),
             'MDM_RESTORE_DATABASE_URL or MDM_RESTORE_DATABASE_URL_FILE is required'),
        ):
            work = directory / name
            prepare(work, archive=archive_present)
            execute(name, restore_script, work, expected=1, remove=remove)
            control = json.loads((work / 'artifacts/second-restore-rejection.json').read_text())
            assert control['passed'] is False and control['returncode'] == 1
            assert control['checks']['expected_reason'] is False
            assert control['response']['reason'] == reason
            controls.append({'name': name, 'workflow_exit': 1, 'restore_exit': 1,
                             'reason': reason, 'wrong_failure_rejected': True})
        report['failure_controls'] = controls
        report['passed'] = True
    finally:
        after = {name: fingerprint(dsn, name) for name, dsn in targets.items()}
        write_json(directory / 'database-after.json', after)
        final_hashes = {str(path.relative_to(REPO)): sha(path) for path in sorted(inputs)}
        write_json(directory / 'source-after.json', final_hashes)
        report['operational_tables_unchanged'] = before == after
        report['source_inputs_unchanged'] = input_hashes == final_hashes
        report['passed'] = report['passed'] and report['operational_tables_unchanged'] and report['source_inputs_unchanged']
        report['finished_at'] = now()
        write_json(directory / 'qualification.json', report)
        print(json.dumps({'report': str(directory / 'qualification.json'), 'passed': report['passed']}), flush=True)
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
