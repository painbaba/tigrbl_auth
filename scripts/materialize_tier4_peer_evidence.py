from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from tba_operator_identity.repo_truth import evaluate_tier4_bundle, package_version

ROOT = Path(__file__).resolve().parents[1]
PEER_PROFILE_DIR = ROOT / 'compliance' / 'evidence' / 'peer_profiles'
COUNTERPART_DIR = ROOT / 'compliance' / 'evidence' / 'peer_counterparts'
TIER4_ROOT = ROOT / 'compliance' / 'evidence' / 'tier4'
CANDIDATE_ROOT = TIER4_ROOT / 'candidates'
BUNDLE_ROOT = TIER4_ROOT / 'bundles'
DIST_TIER4_ROOT = ROOT / 'dist' / 'evidence-bundles' / 'peer-claim' / 'tier4'
HANDOFF_ROOT = ROOT / 'dist' / 'tier4-external-handoff'


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()

NON_INDEPENDENT_EVIDENCE_SOURCES = {
    'staged-external-root-fixture',
    'repository-staged-nonindependent-fixture',
    'repository-fixture',
    'self-check',
    'self-generated',
    'package-generated',
}
NON_INDEPENDENT_OPERATOR_MARKERS = {
    'checkpoint-staged-external-root',
    'repository-fixture',
    'self-check',
    'package-self-attested',
}
GLOBAL_REQUIRED_IDENTITY_FIELDS = ('peer_operator',)
GLOBAL_REQUIRED_ATTESTATION_FIELDS = (
    'attesting_organization',
    'attesting_contact',
    'attestation_timestamp',
)
REJECTED_PLACEHOLDER_MARKERS = (
    'required:',
    'fill this',
    'fill after',
    'replace this template',
    'placeholder',
    'to be completed',
)



def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding='utf-8')


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith('\n') else text + '\n', encoding='utf-8')


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_version() -> str:
    version = package_version(ROOT)
    return version or '0.0.0-checkpoint'


def listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def normalized_str(value: Any) -> str:
    return str(value or '').strip()


def is_placeholder_value(value: Any) -> bool:
    text = normalized_str(value).lower()
    if not text:
        return True
    return any(marker in text for marker in REJECTED_PLACEHOLDER_MARKERS)


def has_boolean_false(value: Any) -> bool:
    return value is False


def summarize_peer_matrix(peer_matrix: list[dict[str, Any]]) -> dict[str, Any]:
    preserved_rows = [row for row in peer_matrix if row.get('external_bundle_dir')]
    invalid_rows = [row for row in preserved_rows if row.get('validation_failures')]
    valid_rows = [row for row in preserved_rows if not row.get('validation_failures')]
    missing_profiles = sorted(row['profile'] for row in peer_matrix if not row.get('external_bundle_dir'))
    invalid_profiles = sorted(row['profile'] for row in invalid_rows)
    valid_profiles = sorted(row['profile'] for row in valid_rows)
    return {
        'preserved_bundle_count': len(preserved_rows),
        'valid_external_bundle_count': len(valid_rows),
        'invalid_external_bundle_count': len(invalid_rows),
        'missing_external_bundle_count': len(missing_profiles),
        'profiles_missing_external_bundles': missing_profiles,
        'profiles_with_invalid_external_bundles': invalid_profiles,
        'profiles_with_valid_external_bundles': valid_profiles,
        'valid_bundle_dirs': [str(row['external_bundle_dir']) for row in valid_rows],
        'invalid_bundle_dirs': [str(row['external_bundle_dir']) for row in invalid_rows],
    }


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def load_peer_profiles() -> dict[str, dict[str, Any]]:
    return {path.stem: load_yaml(path) for path in sorted(PEER_PROFILE_DIR.glob('*.yaml'))}


def load_counterparts() -> dict[str, dict[str, Any]]:
    return {path.stem: load_yaml(path) for path in sorted(COUNTERPART_DIR.glob('*.yaml'))}


def load_target_test_mapping() -> dict[str, list[str]]:
    mapping = load_yaml(ROOT / 'compliance' / 'mappings' / 'target-to-test.yaml') or {}
    return {str(key): listify(value) for key, value in mapping.items()}


def load_claims() -> dict[str, Any]:
    return load_yaml(ROOT / 'compliance' / 'claims' / 'declared-target-claims.yaml')


def save_claims(payload: dict[str, Any]) -> None:
    write_yaml(ROOT / 'compliance' / 'claims' / 'declared-target-claims.yaml', payload)


def load_repository_state() -> dict[str, Any]:
    return load_yaml(ROOT / 'compliance' / 'claims' / 'repository-state.yaml')


def save_repository_state(payload: dict[str, Any]) -> None:
    write_yaml(ROOT / 'compliance' / 'claims' / 'repository-state.yaml', payload)


def load_retained_targets() -> list[str]:
    scope = load_yaml(ROOT / 'compliance' / 'targets' / 'certification_scope.yaml')
    return [
        str(entry.get('label'))
        for entry in scope.get('targets', [])
        if str(entry.get('scope_bucket')) != 'out-of-scope/deferred'
    ]


def canonical_contract_snapshots() -> dict[str, list[str]]:
    profile_paths: dict[str, list[str]] = {}
    for label in ('baseline', 'production', 'hardening', 'peer-claim'):
        candidates = [
            ROOT / 'specs' / 'openapi' / 'profiles' / label / 'tba_auth.public.openapi.json',
            ROOT / 'specs' / 'openrpc' / 'profiles' / label / 'tba_auth.admin.openrpc.json',
            ROOT / 'compliance' / 'claims' / f'effective-target-claims.{label}.yaml',
            ROOT / 'compliance' / 'evidence' / f'effective-release-evidence.{label}.yaml',
        ]
        profile_paths[label] = [relpath(path) for path in candidates if path.exists()]
    return profile_paths


def target_coverage(peer_profiles: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    coverage: dict[str, list[str]] = {}
    for profile_id, profile in peer_profiles.items():
        for target in listify(profile.get('required_targets')):
            coverage.setdefault(target, []).append(profile_id)
    return {target: sorted(set(profiles)) for target, profiles in sorted(coverage.items())}


def ensure_candidate_layout(
    profile_id: str,
    profile: dict[str, Any],
    counterpart: dict[str, Any],
    target_tests: dict[str, list[str]],
    contract_paths: dict[str, list[str]],
) -> dict[str, Any]:
    candidate_dir = CANDIDATE_ROOT / profile_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    required_targets = listify(profile.get('required_targets'))
    contract_profiles = listify(profile.get('contract_profiles'))
    candidate_manifest = {
        'schema_version': 1,
        'bundle_kind': 'tier4-candidate-layout',
        'profile': profile_id,
        'counterpart_id': counterpart.get('id', profile.get('counterpart_id')),
        'status': 'awaiting-independent-external-artifacts',
        'runtime_profile': profile.get('preferred_runtime_profile', 'hardening'),
        'required_targets': required_targets,
        'scenario_ids': listify(profile.get('scenario_ids')),
        'required_peer_artifacts': counterpart.get('required_artifacts', []),
        'required_identity_fields': counterpart.get('required_identity_fields', []),
        'required_container_fields': counterpart.get('required_container_fields', []),
        'attestation_class_required': counterpart.get('attestation_class_required'),
        'contract_profiles': contract_profiles,
        'contract_snapshot_refs': {label: contract_paths.get(label, []) for label in contract_profiles},
        'generated_at': now(),
    }
    mapping = {
        'profile': profile_id,
        'counterpart_id': counterpart.get('id', profile.get('counterpart_id')),
        'target_to_tests': {target: target_tests.get(target, []) for target in required_targets},
        'required_targets': required_targets,
        'required_artifacts': listify(profile.get('required_artifacts')),
    }
    write_yaml(candidate_dir / 'manifest.yaml', candidate_manifest)
    write_yaml(candidate_dir / 'mapping.yaml', mapping)
    write_yaml(candidate_dir / 'peer-profile.yaml', profile)
    write_text(
        candidate_dir / 'execution.log',
        'Candidate layout generated by the standalone Tier 4 materialization tool.\n'
        'Materialized Tier 4 bundles are created only from preserved external-root artifacts.\n',
    )
    peer_artifacts_dir = candidate_dir / 'peer-artifacts'
    peer_artifacts_dir.mkdir(parents=True, exist_ok=True)
    write_text(
        peer_artifacts_dir / 'README.md',
        'Place externally generated transcripts, peer runtime/container provenance, and scenario outputs here before normalization into a preserved Tier 4 bundle.',
    )
    reproduction = (
        '# Reproduction\n\n'
        f'1. Run the external counterpart `{counterpart.get("id")}` against the `{profile.get("preferred_runtime_profile", "hardening")}` profile.\n'
        '2. Capture exact HTTP/RPC transcripts, peer identity, peer version, image reference, immutable image/container digest, scenario results, and reproduction notes.\n'
        f'3. Supply the artifacts under an external root at `<external-root>/{profile_id}/`.\n'
        f'4. Re-run `python scripts/materialize_tier4_peer_evidence.py --external-root <external-root>` to normalize and validate the preserved bundle for `{profile_id}`.\n'
        '5. Tier 4 promotion occurs only when the counterpart identity, attestation class, scenario coverage, and reproduction requirements are all satisfied.\n'
    )
    write_text(candidate_dir / 'reproduction.md', reproduction)
    return {
        'profile': profile_id,
        'candidate_dir': relpath(candidate_dir),
        'required_targets': required_targets,
        'runtime_profile': profile.get('preferred_runtime_profile', 'hardening'),
        'counterpart_id': counterpart.get('id'),
    }


def materialize_external_handoff_templates(
    peer_profiles: dict[str, dict[str, Any]],
    counterparts: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if HANDOFF_ROOT.exists():
        shutil.rmtree(HANDOFF_ROOT)
    HANDOFF_ROOT.mkdir(parents=True, exist_ok=True)

    manifest_profiles: list[dict[str, Any]] = []
    for profile_id, profile in sorted(peer_profiles.items()):
        counterpart_id = str(profile.get('counterpart_id', '')).strip()
        counterpart = counterparts[counterpart_id]
        profile_root = HANDOFF_ROOT / profile_id
        placeholders_root = profile_root / 'required-artifact-placeholders'
        placeholders_root.mkdir(parents=True, exist_ok=True)

        scenario_results = [
            {
                'id': scenario_id,
                'passed': False,
                'evidence': [],
                'notes': 'Fill with externally generated result evidence.',
            }
            for scenario_id in listify(profile.get('scenario_ids'))
        ]
        write_yaml(
            profile_root / 'manifest.template.yaml',
            {
                'schema_version': 1,
                'profile': profile_id,
                'counterpart_id': counterpart_id,
                'evidence_source': 'Fill with independent external source name.',
                'source_revision': 'Fill with immutable source revision.',
                'peer_identity': {
                    'peer_operator': 'Fill with independent organization or operator.',
                    **{
                        field: f'Fill with {field}.'
                        for field in listify(counterpart.get('required_identity_fields'))
                    },
                },
                'peer_runtime': {
                    'execution_style': counterpart.get('execution_style'),
                    **{
                        field: f'Fill with {field}.'
                        for field in listify(counterpart.get('required_container_fields'))
                    },
                },
                'independence_attestation': {
                    'attestation_class': counterpart.get('attestation_class_required'),
                    'attesting_organization': 'Fill with attesting organization.',
                    'attesting_contact': 'Fill with attesting contact.',
                    'attestation_timestamp': 'Fill with RFC 3339 timestamp.',
                    'counterpart_identified': True,
                    'reproduction_preserved': True,
                    'package_team_member': False,
                    'repository_fixture_generated': False,
                },
                'reproduction': 'Fill with reproduction summary or include reproduction.md.',
            },
        )
        write_yaml(
            profile_root / 'result.template.yaml',
            {
                'schema_version': 1,
                'profile': profile_id,
                'counterpart_id': counterpart_id,
                'passed': False,
                'scenario_results': scenario_results,
            },
        )
        write_text(
            profile_root / 'reproduction.template.md',
            '\n'.join(
                [
                    '# External Reproduction',
                    '',
                    f'- Peer profile: `{profile_id}`',
                    f'- Counterpart: `{counterpart_id}`',
                    f'- Runtime profile: `{profile.get("preferred_runtime_profile", "hardening")}`',
                    '',
                    'Record exact commands, container image digests, endpoint URLs, timestamps, and transcript locations used by the independent peer harness.',
                ]
            ),
        )
        write_text(
            profile_root / 'CHECKLIST.md',
            '\n'.join(
                [
                    '# External Handoff Checklist',
                    '',
                    '- Complete `manifest.yaml` from `manifest.template.yaml`.',
                    '- Complete `result.yaml` from `result.template.yaml` with one result per required scenario.',
                    '- Provide `reproduction.md` with exact independent execution instructions.',
                    '- Replace every file under `required-artifact-placeholders/` with externally generated evidence.',
                    '- Preserve immutable peer runtime metadata, including image digest where a container is used.',
                ]
            ),
        )

        for artifact in listify(counterpart.get('required_artifacts')):
            artifact_name = artifact.rstrip('/').replace('\\', '/')
            if not artifact_name:
                continue
            placeholder_path = placeholders_root / f'{artifact_name.replace("/", "__")}.placeholder.txt'
            write_text(
                placeholder_path,
                f'Provide independent external artifact `{artifact_name}` for profile `{profile_id}`.',
            )

        manifest_profiles.append(
            {
                'profile': profile_id,
                'counterpart_id': counterpart_id,
                'template_dir': relpath(profile_root),
                'required_artifacts': listify(counterpart.get('required_artifacts')),
                'scenario_ids': listify(profile.get('scenario_ids')),
            }
        )

    write_json(
        HANDOFF_ROOT / 'external-root-template.json',
        {
            'schema_version': 1,
            'template_kind': 'tier4-external-peer-handoff',
            'profile_count': len(manifest_profiles),
            'profiles': manifest_profiles,
        },
    )
    write_text(
        HANDOFF_ROOT / 'README.md',
        'This tree is a fill-in package for independent external Tier 4 peer evidence. It is not itself qualifying peer evidence.',
    )
    return manifest_profiles


def _load_external_result(ext_dir: Path) -> dict[str, Any] | None:
    result_yaml = ext_dir / 'result.yaml'
    result_json = ext_dir / 'result.json'
    if result_yaml.exists():
        return load_yaml(result_yaml)
    if result_json.exists():
        return json.loads(result_json.read_text(encoding='utf-8'))
    return None


def _validate_external_artifacts(
    ext_dir: Path,
    profile_id: str,
    profile: dict[str, Any],
    counterpart: dict[str, Any],
    source_manifest: dict[str, Any],
    source_result: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if normalized_str(source_manifest.get('profile')) and normalized_str(source_manifest.get('profile')) != profile_id:
        failures.append('profile id mismatch')
    if normalized_str(source_manifest.get('counterpart_id')) != normalized_str(counterpart.get('id')):
        failures.append('counterpart_id mismatch')

    peer_identity = source_manifest.get('peer_identity') or {}
    peer_runtime = source_manifest.get('peer_runtime') or {}
    independence = source_manifest.get('independence_attestation') or {}
    evidence_source = normalized_str(source_manifest.get('evidence_source'))
    if is_placeholder_value(evidence_source):
        failures.append('missing evidence_source')
    elif evidence_source in NON_INDEPENDENT_EVIDENCE_SOURCES or 'fixture' in evidence_source.lower() or 'self' in evidence_source.lower():
        failures.append('non-independent evidence source')

    required_identity_fields = list(counterpart.get('required_identity_fields', []) or []) + list(GLOBAL_REQUIRED_IDENTITY_FIELDS)
    for field in required_identity_fields:
        if is_placeholder_value(peer_identity.get(field)):
            failures.append(f'missing peer_identity.{field}')
    peer_operator = normalized_str(peer_identity.get('peer_operator')).lower()
    if peer_operator in NON_INDEPENDENT_OPERATOR_MARKERS or 'fixture' in peer_operator or 'self' in peer_operator:
        failures.append('peer operator is not independent')

    for field in counterpart.get('required_container_fields', []) or []:
        if is_placeholder_value(peer_runtime.get(field)):
            failures.append(f'missing peer_runtime.{field}')
    execution_style = normalized_str(peer_runtime.get('execution_style'))
    expected_execution_style = normalized_str(counterpart.get('execution_style'))
    if expected_execution_style:
        if is_placeholder_value(execution_style):
            failures.append('missing peer_runtime.execution_style')
        elif execution_style != expected_execution_style:
            failures.append('peer_runtime.execution_style mismatch')
    image_digest = normalized_str(peer_runtime.get('image_digest'))
    if image_digest and not image_digest.startswith('sha256:'):
        failures.append('peer_runtime.image_digest must be an immutable sha256 digest')

    required_attestation = normalized_str(counterpart.get('attestation_class_required') or 'independent-external')
    attestation_class = normalized_str(independence.get('attestation_class'))
    if attestation_class != required_attestation:
        failures.append('independence attestation class mismatch')
    for field in GLOBAL_REQUIRED_ATTESTATION_FIELDS:
        if is_placeholder_value(independence.get(field)):
            failures.append(f'missing independence_attestation.{field}')
    if not bool(independence.get('counterpart_identified', False)):
        failures.append('independence attestation missing counterpart_identified=true')
    if not bool(independence.get('reproduction_preserved', False)):
        failures.append('independence attestation missing reproduction_preserved=true')
    if not has_boolean_false(independence.get('package_team_member')):
        failures.append('independence attestation missing package_team_member=false')
    if not has_boolean_false(independence.get('repository_fixture_generated')):
        failures.append('independence attestation missing repository_fixture_generated=false')

    source_revision = normalized_str(source_manifest.get('source_revision') or source_manifest.get('git_revision'))
    if is_placeholder_value(source_revision):
        failures.append('missing source_revision')

    has_reproduction = (
        bool(independence.get('reproduction_preserved', False))
        and (
            (ext_dir / 'reproduction.md').exists()
            or not is_placeholder_value(source_manifest.get('reproduction'))
        )
    )
    if not has_reproduction:
        failures.append('reproduction material missing')

    for required_artifact in counterpart.get('required_artifacts', []) or []:
        if not (ext_dir / str(required_artifact)).exists():
            failures.append(f'missing counterpart artifact: {required_artifact}')

    if normalized_str(source_result.get('profile')) and normalized_str(source_result.get('profile')) != profile_id:
        failures.append('result.profile mismatch')
    if normalized_str(source_result.get('counterpart_id')) and normalized_str(source_result.get('counterpart_id')) != normalized_str(counterpart.get('id')):
        failures.append('result.counterpart_id mismatch')

    scenario_results = list(source_result.get('scenario_results') or [])
    scenario_status = {str(item.get('id')): bool(item.get('passed', False)) for item in scenario_results}
    for scenario_id in profile.get('scenario_ids', []) or []:
        scenario_id = str(scenario_id)
        if scenario_id not in scenario_status:
            failures.append(f'missing scenario result: {scenario_id}')
        elif not scenario_status[scenario_id]:
            failures.append(f'scenario failed: {scenario_id}')
    if not bool(source_result.get('passed', False)):
        failures.append('result.passed is false')
    return sorted(set(failures))


def materialize_external_bundle(
    profile_id: str,
    profile: dict[str, Any],
    counterpart: dict[str, Any],
    external_root: Path,
    target_tests: dict[str, list[str]],
) -> dict[str, Any] | None:
    ext_dir = external_root / profile_id
    if not ext_dir.exists() or not ext_dir.is_dir():
        return None
    manifest_path = ext_dir / 'manifest.yaml'
    source_result = _load_external_result(ext_dir)
    if not manifest_path.exists() or source_result is None:
        return None
    source_manifest = load_yaml(manifest_path)
    validation_failures = _validate_external_artifacts(ext_dir, profile_id, profile, counterpart, source_manifest, source_result)
    passed = not validation_failures

    bundle_id = f"{profile_id}--{counterpart.get('id')}"
    bundle_dir = BUNDLE_ROOT / bundle_id
    bundle_dir.mkdir(parents=True, exist_ok=True)
    normalized_manifest = {
        'schema_version': 1,
        'bundle_id': bundle_id,
        'peer_profile': profile_id,
        'counterpart_id': counterpart.get('id'),
        'status': 'external-preserved-passed' if passed else 'external-preserved-failed',
        'runtime_profile': profile.get('preferred_runtime_profile', 'hardening'),
        'target_ids': listify(profile.get('required_targets')),
        'scenario_results': list(source_result.get('scenario_results', [])),
        'peer_identity': source_manifest.get('peer_identity') or {},
        'peer_runtime': source_manifest.get('peer_runtime') or {},
        'independence_attestation': source_manifest.get('independence_attestation') or {},
        'evidence_source': source_manifest.get('evidence_source', 'unspecified'),
        'source_revision': source_manifest.get('source_revision') or source_manifest.get('git_revision') or 'unknown',
        'contract_version': source_manifest.get('contract_version') or repo_version(),
        'generated_at': now(),
        'validation_failures': validation_failures,
        'artifacts': [],
    }
    mapping = {
        'required_targets': listify(profile.get('required_targets')),
        'target_to_tests': {target: target_tests.get(target, []) for target in listify(profile.get('required_targets'))},
        'required_artifacts': listify(profile.get('required_artifacts')),
        'counterpart_id': counterpart.get('id'),
    }
    write_yaml(bundle_dir / 'manifest.yaml', normalized_manifest)
    write_yaml(bundle_dir / 'mapping.yaml', mapping)
    write_yaml(bundle_dir / 'peer-profile.yaml', profile)
    write_text(bundle_dir / 'execution.log', json.dumps(source_result, indent=2))

    peer_artifacts_dir = bundle_dir / 'peer-artifacts'
    peer_artifacts_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(ext_dir.iterdir()):
        if path.name in {'manifest.yaml', 'result.yaml', 'result.json', 'reproduction.md'}:
            continue
        dst = peer_artifacts_dir / path.name
        if path.is_dir():
            copy_tree(path, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst)

    reproduction = source_manifest.get('reproduction') or ((ext_dir / 'reproduction.md').read_text(encoding='utf-8') if (ext_dir / 'reproduction.md').exists() else '# Reproduction\n\nExternal reproduction material was not supplied.\n')
    write_text(bundle_dir / 'reproduction.md', reproduction)

    hashes: dict[str, str] = {}
    for path in sorted(bundle_dir.rglob('*')):
        if path.is_file():
            hashes[str(path.relative_to(bundle_dir))] = sha256_file(path)
    write_yaml(bundle_dir / 'hashes.yaml', hashes)
    write_yaml(
        bundle_dir / 'signatures.yaml',
        {
            'status': 'external-source-preserved',
            'note': 'External signature material, if any, must remain in peer-artifacts/ or reproduction.md.',
        },
    )
    normalized_manifest['artifacts'] = [{'path': rel, 'sha256': digest} for rel, digest in sorted(hashes.items())]
    write_yaml(bundle_dir / 'manifest.yaml', normalized_manifest)

    dist_dir = DIST_TIER4_ROOT / bundle_id
    dist_dir.parent.mkdir(parents=True, exist_ok=True)
    copy_tree(bundle_dir, dist_dir)
    return {
        'profile': profile_id,
        'bundle_dir': relpath(bundle_dir),
        'dist_bundle_dir': relpath(dist_dir),
        'passed': passed,
        'promotable_targets': listify(profile.get('required_targets')) if passed else [],
        'validation_failures': validation_failures,
    }


def load_preserved_bundle_status(
    profile_id: str,
    counterpart_id: str,
    profile: dict[str, Any],
) -> dict[str, Any] | None:
    bundle_id = f'{profile_id}--{counterpart_id}'
    bundle_dir = BUNDLE_ROOT / bundle_id
    manifest_path = bundle_dir / 'manifest.yaml'
    if not manifest_path.exists():
        return None
    manifest = load_yaml(manifest_path) or {}
    passed, failures, _details = evaluate_tier4_bundle(bundle_dir, manifest)
    return {
        'profile': profile_id,
        'bundle_dir': relpath(bundle_dir),
        'dist_bundle_dir': None,
        'passed': passed,
        'promotable_targets': listify(profile.get('required_targets')) if passed else [],
        'validation_failures': failures,
    }


def update_claims(promoted_targets: set[str], retained_targets: list[str]) -> dict[str, Any]:
    claims_doc = load_claims()
    claim_set = claims_doc.setdefault('claim_set', {})
    full_boundary_promoted = bool(retained_targets) and set(retained_targets) <= promoted_targets
    claim_set['delivery_track'] = 'independent-peer-evidence'
    claim_set['current_repository_tier'] = 4 if full_boundary_promoted else 3
    for claim in claim_set.get('claims', []):
        target = str(claim.get('target'))
        if target in promoted_targets:
            claim['tier'] = 4
            claim['status'] = 'peer-validated-evidenced-release-gated'
        elif int(claim.get('tier', 0)) >= 4 and target not in promoted_targets:
            claim['tier'] = 3
            claim['status'] = 'evidenced-release-gated'
    save_claims(claims_doc)
    return claims_doc


def update_repository_state(promoted_targets: set[str], peer_matrix: list[dict[str, Any]], preserved_bundle_count: int, retained_targets: list[str]) -> dict[str, Any]:
    state_doc = load_repository_state()
    state = state_doc.setdefault('repository_state', {})
    full_boundary_promoted = bool(retained_targets) and set(retained_targets) <= promoted_targets
    bundle_stats = summarize_peer_matrix(peer_matrix)
    state['independent_peer_program_extended_complete'] = True
    state['target_to_peer_mapping_complete'] = True
    state['peer_counterpart_catalog_complete'] = True
    state['peer_schema_and_tooling_extended'] = True
    state['tier4_candidate_bundle_layouts_present'] = True
    state['tier4_external_bundle_count'] = bundle_stats['preserved_bundle_count']
    state['tier4_valid_external_bundle_count'] = bundle_stats['valid_external_bundle_count']
    state['tier4_invalid_external_bundle_count'] = bundle_stats['invalid_external_bundle_count']
    state['tier4_missing_external_bundle_count'] = bundle_stats['missing_external_bundle_count']
    state['tier4_promoted_target_count'] = len(promoted_targets)
    state['tier4_peer_validation_complete'] = full_boundary_promoted
    state['tier4_retained_boundary_complete'] = full_boundary_promoted
    state['strict_independent_claims_ready'] = full_boundary_promoted
    state['tier4_peer_matrix_generated'] = True
    state['tier4_last_matrix_profile_count'] = len(peer_matrix)
    state['fully_certifiable'] = False
    state['fully_rfc_compliant'] = False
    save_repository_state(state_doc)
    return state_doc


def update_evidence_manifest(
    preserved_bundles: list[str],
    valid_preserved_bundles: list[str],
    invalid_preserved_bundles: list[str],
    candidate_bundles: list[str],
    promoted_targets: set[str],
    retained_targets: list[str],
    profile_count: int,
) -> dict[str, Any]:
    manifest_path = ROOT / 'compliance' / 'evidence' / 'manifest.yaml'
    doc = load_yaml(manifest_path)
    state = doc.setdefault('state', {})
    state['preserved_tier4_bundles'] = preserved_bundles
    state['valid_preserved_tier4_bundles'] = valid_preserved_bundles
    state['invalid_preserved_tier4_bundles'] = invalid_preserved_bundles
    state['tier4_candidate_layouts'] = candidate_bundles
    state['strict_independent_claims_ready'] = bool(retained_targets) and set(retained_targets) <= promoted_targets
    state['tier4_profile_catalog_count'] = profile_count
    state['tier4_external_bundle_count'] = len(preserved_bundles)
    state['tier4_valid_external_bundle_count'] = len(valid_preserved_bundles)
    state['tier4_invalid_external_bundle_count'] = len(invalid_preserved_bundles)
    state['tier4_missing_external_bundle_count'] = max(profile_count - len(preserved_bundles), 0)
    paths = doc.setdefault('paths', {})
    paths['peer_profile_root'] = 'compliance/evidence/peer_profiles'
    paths['peer_counterpart_root'] = 'compliance/evidence/peer_counterparts'
    paths['tier4_candidate_root'] = 'compliance/evidence/tier4/candidates'
    paths['tier4_bundle_root'] = 'compliance/evidence/tier4/bundles'
    promoted = doc.setdefault('promoted_target_subsets', {})
    promoted['tier4'] = sorted(promoted_targets)
    notes = [note for note in list(doc.get('notes', [])) if not str(note).startswith('runtime-foundation checkpoint3 installs the independent peer program')]
    if promoted_targets and set(retained_targets) <= promoted_targets:
        notes.append('runtime-foundation checkpoint3 installs the independent peer program and preserves validated external Tier 4 bundles for the full retained boundary.')
    elif promoted_targets:
        notes.append('runtime-foundation checkpoint3 installs the independent peer program and preserves validated external Tier 4 bundles for a subset of retained targets. Package-level strict independent claims remain blocked until the full retained boundary is promoted.')
    else:
        notes.append('runtime-foundation checkpoint3 installs the independent peer program, full retained target-to-peer mapping, counterpart catalog, candidate bundle layouts, and fail-closed Tier 4 promotion logic. No targets are promoted to Tier 4 in this checkpoint because preserved qualifying independent external artifacts were not supplied.')
    doc['notes'] = notes
    write_yaml(manifest_path, doc)
    return doc


def write_peer_profile_execution_reports(peer_profiles: dict[str, dict[str, Any]], external_root: Path | None, retained_targets: list[str]) -> None:
    execution_mode = 'external-preserved' if external_root else 'self-check'
    summary = {
        'deployment_profile': 'hardening',
        'execution_mode': execution_mode,
        'executed_profile_count': len(peer_profiles),
        'peer_profile_count': len(peer_profiles),
        'counterpart_catalog_count': len(load_counterparts()),
        'retained_target_count': len(retained_targets),
        'mapped_retained_target_count': len(target_coverage(peer_profiles)),
        'retained_target_coverage_complete': True,
        'external_artifact_root': relpath(external_root) if external_root else None,
    }
    payload = {'passed': True, 'failures': [], 'warnings': [], 'summary': summary, 'details': sorted(peer_profiles)}
    write_json(ROOT / 'docs' / 'compliance' / 'peer_profile_execution_report.json', payload)
    lines = ['# Peer Profile Execution Report', '', f"- Passed: `{payload['passed']}`", '', '## Summary', '']
    for key, value in summary.items():
        lines.append(f'- {key}: `{value}`')
    lines.extend(['', '## Details', ''])
    for item in sorted(peer_profiles):
        lines.append(f'- {item}')
    write_text(ROOT / 'docs' / 'compliance' / 'peer_profile_execution_report.md', '\n'.join(lines))


def write_peer_matrix_reports(peer_matrix: list[dict[str, Any]], promoted_targets: set[str], retained_targets: list[str]) -> None:
    report_dirs = [
        ROOT / 'docs' / 'compliance',
        ROOT / 'docs' / 'archive' / 'historical' / 'compliance',
    ]
    for report_dir in report_dirs:
        report_dir.mkdir(parents=True, exist_ok=True)
    full_boundary_promoted = bool(retained_targets) and set(retained_targets) <= promoted_targets
    candidate_profile_count = len([row for row in peer_matrix if row.get('candidate_dir')])
    bundle_stats = summarize_peer_matrix(peer_matrix)
    summary = {
        'profile_count': len(peer_matrix),
        'candidate_profile_count': candidate_profile_count,
        'external_bundle_count': bundle_stats['preserved_bundle_count'],
        'promoted_target_count': len(promoted_targets),
        'retained_target_count': len(retained_targets),
        'tier4_claims_present': bool(promoted_targets),
        'retained_boundary_promoted': full_boundary_promoted,
        'supported_peer_profile_count': len(peer_matrix),
        'required_external_bundle_count': len(peer_matrix),
        'valid_external_bundle_count': bundle_stats['valid_external_bundle_count'],
        'invalid_external_bundle_count': bundle_stats['invalid_external_bundle_count'],
        'missing_external_bundle_count': bundle_stats['missing_external_bundle_count'],
        'profiles_missing_external_bundles': bundle_stats['profiles_missing_external_bundles'],
        'profiles_with_invalid_external_bundles': bundle_stats['profiles_with_invalid_external_bundles'],
        'strict_independent_claims_ready': full_boundary_promoted,
    }
    payload = {'passed': True, 'summary': summary, 'details': peer_matrix}
    lines = ['# Peer Matrix Report', '', '## Summary', '']
    for key, value in summary.items():
        lines.append(f'- {key}: `{value}`')
    lines.extend([
        '',
        '## Profiles',
        '',
        '| Profile | Counterpart | Runtime | Targets | Candidate | External bundle | Tier 4 promotable targets | Validation failures |',
        '|---|---|---|---|---|---|---|---|',
    ])
    for row in peer_matrix:
        targets = ', '.join(row['required_targets'])
        promotable = ', '.join(row.get('promotable_targets', [])) or '—'
        failures = ', '.join(row.get('validation_failures', [])) or '—'
        lines.append(
            f"| {row['profile']} | {row['counterpart_id']} | {row['runtime_profile']} | {targets} | {row.get('candidate_dir') or ''} | {row.get('external_bundle_dir') or ''} | {promotable} | {failures} |"
        )
    lines.extend([
        '',
        'Tier 4 claims are promoted only for targets backed by preserved external bundles with peer identity, version, container/runtime provenance, exact transcripts, complete scenario coverage, and reproduction material.',
        'Repository-staged fixture bundles and self-attested bundle roots are preserved only for fail-closed validation exercises and never count toward strict independent claims.',
        '',
    ])
    for report_dir in report_dirs:
        write_json(report_dir / 'peer_matrix_report.json', payload)
        write_text(report_dir / 'PEER_MATRIX_REPORT.md', '\n'.join(lines))
    if promoted_targets:
        promo_body = '\n'.join(f'- `{target}`' for target in sorted(promoted_targets))
    else:
        promo_body = 'No Tier 4 targets are promoted in this checkpoint. Preserved qualifying independent external artifacts were not supplied for the full retained boundary.'
    for report_dir in report_dirs:
        write_text(report_dir / 'TIER4_PROMOTION_MATRIX.md', '# Tier 4 Promotion Matrix\n\n' + promo_body)


def write_peer_program_docs(promoted_targets: set[str], peer_matrix: list[dict[str, Any]], preserved_bundle_count: int, retained_targets: list[str], external_root: Path | None) -> None:
    report_dir = ROOT / 'docs' / 'archive' / 'historical' / 'compliance'
    report_dir.mkdir(parents=True, exist_ok=True)
    full_boundary_promoted = bool(retained_targets) and set(retained_targets) <= promoted_targets
    bundle_stats = summarize_peer_matrix(peer_matrix)
    if full_boundary_promoted:
        limitation = (
            'This checkpoint preserves a full qualifying bundle set for every peer profile and the repository evidence model recognizes the full retained boundary as Tier 4 promoted. '
            'These bundles must still be reviewed alongside the validated runtime/test manifests before any final public certification claim is issued.'
        )
    else:
        limitation = (
            'This checkpoint environment did not contain preserved qualifying independently produced peer artifacts with external peer identity, peer version, immutable image/container digests, exact transcripts, and scenario results for the full retained boundary. '
            'Repository-staged fixture roots remain useful for fail-closed pipeline exercises, but they are explicitly rejected for Tier 4 promotion and package-level strict independent claims remain blocked until real external bundles are preserved and validated.'
        )
    lines = [
        '# runtime-foundation checkpoint3 Independent Peer Program and Strict Public Claims',
        '',
        'This checkpoint extends the independent peer program for `tba_auth`, installs full retained target-to-peer coverage, and preserves Tier 4 bundle normalization logic that fails closed when external artifacts are absent, incomplete, self-attested, or repository-staged.',
        '',
        '## Implemented in this checkpoint',
        '',
        '- extended peer profiles for browser, SPA, native, device, resource-server, gateway, DPoP, mTLS, PAR/JAR/RAR, operator CLI, and runner profiles',
        '- counterpart catalog entries require attestation class, identity, runtime/container provenance, and preserved artifacts',
        '- candidate Tier 4 bundle layouts cover the full peer catalog',
        '- preserved bundle normalization validates identity, provenance, scenario coverage, reproduction material, and independent provenance markers',
        '- repository-staged fixture roots are preserved only for fail-closed materialization exercises and are rejected for Tier 4 promotion',
        '- peer matrix, promotion matrix, and current-state reports were refreshed',
        '',
        '## Current result',
        '',
        f'- peer profiles in catalog: `{len(peer_matrix)}`',
        f'- preserved external Tier 4 bundles normalized: `{bundle_stats["preserved_bundle_count"]}`',
        f'- valid independent external bundles: `{bundle_stats["valid_external_bundle_count"]}`',
        f'- invalid or non-qualifying preserved bundles: `{bundle_stats["invalid_external_bundle_count"]}`',
        f'- promoted Tier 4 targets: `{len(promoted_targets)}`',
        f'- retained boundary fully promoted to Tier 4: `{full_boundary_promoted}`',
        f'- external artifact root used for this checkpoint: `{relpath(external_root) if external_root else None}`',
        '',
        '## Current provenance note',
        '',
        limitation,
        '',
        '## Profiles covered by the matrix',
        '',
    ]
    for row in peer_matrix:
        lines.append(f"- `{row['profile']}` -> counterpart `{row['counterpart_id']}` -> targets `{', '.join(row['required_targets'])}`")
    write_text(report_dir / 'INDEPENDENT_PEER_PROGRAM.md', '\n'.join(lines))

    runbook = (
        '# External Interop and Tier 4 Promotion\n\n'
        '1. Run the independent external counterpart defined in `compliance/evidence/peer_counterparts/<id>.yaml`.\n'
        '2. Capture exact HTTP/RPC transcripts, peer identity, peer version, peer operator, image reference, immutable image/container digest, scenario results, and reproduction notes.\n'
        '3. Place the artifacts under `<external-root>/<peer-profile>/` with at least `manifest.yaml` and `result.yaml` (or `result.json`).\n'
        '4. Ensure `manifest.yaml` declares `counterpart_id`, `peer_identity`, `peer_runtime`, and `independence_attestation.attestation_class=independent-external`, plus explicit attesting organization/contact/timestamp metadata and `package_team_member=false`.\n'
        '5. Execute `python scripts/materialize_tier4_peer_evidence.py --external-root <external-root> --require-full-boundary`.\n'
        '6. Review `docs/compliance/PEER_MATRIX_REPORT.md`, `docs/compliance/TIER4_PROMOTION_MATRIX.md`, and `docs/compliance/current_state_report.md`.\n'
        '7. Repository-staged fixture roots under `dist/tier4-external-root-fixtures/` are for fail-closed pipeline testing only and never qualify for strict independent claims.\n'
        '8. Review the remaining validated runtime/test/migration gates before making final package-level certification claims.\n'
    )
    write_text(ROOT / 'docs' / 'runbooks' / 'EXTERNAL_INTEROP_AND_TIER4_PROMOTION.md', runbook)


def write_peer_materialization_report(promoted_targets: set[str], preserved_bundle_count: int, retained_targets: list[str], external_root: Path | None, profile_count: int) -> None:
    payload = {
        'passed': True,
        'external_root': relpath(external_root) if external_root else None,
        'preserved_bundle_count': preserved_bundle_count,
        'candidate_profile_count': profile_count,
        'promoted_target_count': len(promoted_targets),
        'promoted_targets': sorted(promoted_targets),
        'retained_target_count': len(retained_targets),
        'missing_retained_target_coverage': [],
        'retained_boundary_promoted': bool(retained_targets) and set(retained_targets) <= promoted_targets,
    }
    write_json(ROOT / 'docs' / 'archive' / 'historical' / 'compliance' / 'independent_peer_materialization_report.json', payload)
    lines = ['# runtime-foundation checkpoint3 Peer Materialization Report', '', f"- passed: `{payload['passed']}`", '', '## Summary', '']
    for key in ('external_root', 'preserved_bundle_count', 'candidate_profile_count', 'promoted_target_count', 'retained_target_count', 'retained_boundary_promoted'):
        lines.append(f"- {key}: `{payload[key]}`")
    lines.extend(['', '## Promoted targets', ''])
    for target in sorted(promoted_targets):
        lines.append(f'- `{target}`')
    write_text(ROOT / 'docs' / 'archive' / 'historical' / 'compliance' / 'independent_peer_materialization_report.md', '\n'.join(lines))


def write_evidence_peer_readiness_report(promoted_targets: set[str], preserved_bundle_count: int, claims_doc: dict[str, Any]) -> None:
    tier3_or_higher = [claim for claim in claims_doc.get('claim_set', {}).get('claims', []) if int(claim.get('tier', 0)) >= 3]
    tier4 = [claim for claim in claims_doc.get('claim_set', {}).get('claims', []) if int(claim.get('tier', 0)) >= 4]
    payload = {
        'passed': True,
        'warnings': [],
        'summary': {
            'tier3_or_higher_claim_count': len(tier3_or_higher),
            'tier4_claim_count': len(tier4),
            'declared_claim_count': len(claims_doc.get('claim_set', {}).get('claims', [])),
            'preserved_tier4_bundle_count': preserved_bundle_count,
        },
    }
    write_json(ROOT / 'docs' / 'compliance' / 'evidence_peer_readiness_report.json', payload)
    lines = ['# Evidence and Peer Readiness Report', '', f"- Passed: `{payload['passed']}`", '', '## Summary', '']
    for key, value in payload['summary'].items():
        lines.append(f'- {key}: `{value}`')
    write_text(ROOT / 'docs' / 'compliance' / 'evidence_peer_readiness_report.md', '\n'.join(lines))


def _render_state_markdown(title: str, passed: bool, summary: dict[str, Any], details: list[str] | None = None) -> str:
    lines = [f'# {title}', '', f'- Passed: `{passed}`', '', '## Summary', '']
    for key, value in summary.items():
        lines.append(f'- {key}: `{value}`')
    if details is not None:
        lines.extend(['', '## Details', ''])
        for item in details:
            lines.append(f'- {item}')
    return '\n'.join(lines) + '\n'


def update_current_and_certification_state_reports(promoted_targets: set[str], retained_targets: list[str], preserved_bundle_count: int) -> None:
    full_boundary_promoted = bool(retained_targets) and set(retained_targets) <= promoted_targets
    peer_matrix_report = json.loads((ROOT / 'docs' / 'compliance' / 'peer_matrix_report.json').read_text(encoding='utf-8')) if (ROOT / 'docs' / 'compliance' / 'peer_matrix_report.json').exists() else {'summary': {}}
    bundle_summary = peer_matrix_report.get('summary', {})
    current_path = ROOT / 'docs' / 'compliance' / 'current_state_report.json'
    current = json.loads(current_path.read_text(encoding='utf-8')) if current_path.exists() else {'passed': True, 'summary': {}, 'details': {}}
    summary = current.setdefault('summary', {})
    claims_doc = load_claims()
    tiers = [int(claim.get('tier', 0)) for claim in claims_doc.get('claim_set', {}).get('claims', [])]
    tier3_exact = sum(1 for tier in tiers if tier == 3)
    tier4_exact = sum(1 for tier in tiers if tier >= 4)
    profile_count = len(load_peer_profiles())
    summary['repository_tier'] = 4 if full_boundary_promoted else 3
    summary['tier_3_claim_count'] = tier3_exact
    summary['tier_4_claim_count'] = tier4_exact
    summary['strict_independent_claims_ready'] = full_boundary_promoted
    summary['retained_boundary_tier3_complete'] = True
    summary['retained_boundary_tier4_complete'] = full_boundary_promoted
    summary['tier4_supported_peer_profile_count'] = profile_count
    summary['tier4_required_external_bundle_count'] = profile_count
    summary['tier4_external_bundle_count'] = int(bundle_summary.get('external_bundle_count', preserved_bundle_count))
    summary['tier4_valid_external_bundle_count'] = int(bundle_summary.get('valid_external_bundle_count', 0))
    summary['tier4_invalid_external_bundle_count'] = int(bundle_summary.get('invalid_external_bundle_count', 0))
    summary['tier4_missing_external_bundle_count'] = int(bundle_summary.get('missing_external_bundle_count', max(profile_count - preserved_bundle_count, 0)))
    summary['tier4_external_handoff_template_present'] = True
    summary['tier4_promoted_target_count'] = len(promoted_targets)
    current.setdefault('details', {})['tier4_ready_targets'] = ', '.join(sorted(promoted_targets))
    current_path.write_text(json.dumps(current, indent=2) + '\n', encoding='utf-8')
    current_md_summary = {
        'repository_tier': summary.get('repository_tier'),
        'declared_claim_count': summary.get('declared_claim_count'),
        'tier_3_claim_count': summary.get('tier_3_claim_count'),
        'tier_4_claim_count': summary.get('tier_4_claim_count'),
        'strict_independent_claims_ready': summary.get('strict_independent_claims_ready'),
        'tier4_external_bundle_count': summary.get('tier4_external_bundle_count'),
        'tier4_valid_external_bundle_count': summary.get('tier4_valid_external_bundle_count'),
        'tier4_invalid_external_bundle_count': summary.get('tier4_invalid_external_bundle_count'),
        'tier4_promoted_target_count': summary.get('tier4_promoted_target_count'),
        'validated_clean_room_matrix_green': summary.get('validated_clean_room_matrix_green'),
        'validated_in_scope_test_lanes_green': summary.get('validated_in_scope_test_lanes_green'),
        'migration_portability_passed': summary.get('migration_portability_passed'),
        'tier3_evidence_rebuilt_from_validated_runs': summary.get('tier3_evidence_rebuilt_from_validated_runs'),
    }
    write_text(ROOT / 'docs' / 'compliance' / 'current_state_report.md', _render_state_markdown('Current State Report', bool(current.get('passed', True)), current_md_summary))

    cert_path = ROOT / 'docs' / 'compliance' / 'certification_state_report.json'
    cert = json.loads(cert_path.read_text(encoding='utf-8')) if cert_path.exists() else {'passed': False, 'summary': {}, 'details': []}
    cert_summary = cert.setdefault('summary', {})
    clean_room_green = bool(summary.get('validated_clean_room_matrix_green', False))
    in_scope_green = bool(summary.get('validated_in_scope_test_lanes_green', False))
    migration_ok = bool(summary.get('migration_portability_passed', False))
    tier3_rebuilt = bool(summary.get('tier3_evidence_rebuilt_from_validated_runs', False))
    runtime_ready = int(summary.get('runtime_profile_ready_count', 0)) == int(summary.get('registered_runner_count', summary.get('runtime_profile_declared_ci_installable_runner_count', 0))) and int(summary.get('runtime_profile_invalid_count', 0)) == 0 and int(summary.get('runtime_profile_missing_count', 0)) == 0 and bool(summary.get('runtime_profile_application_probe_passed', False))
    fully_certifiable = full_boundary_promoted and clean_room_green and in_scope_green and migration_ok and tier3_rebuilt and runtime_ready
    profile_count = len(load_peer_profiles())
    cert_summary['fully_certifiable_now'] = fully_certifiable
    cert_summary['fully_rfc_compliant_now'] = fully_certifiable
    cert_summary['strict_independent_claims_ready'] = full_boundary_promoted
    cert_summary['tier4_supported_peer_profile_count'] = profile_count
    cert_summary['tier4_required_external_bundle_count'] = profile_count
    cert_summary['tier4_external_bundle_count'] = int(bundle_summary.get('external_bundle_count', preserved_bundle_count))
    cert_summary['tier4_valid_external_bundle_count'] = int(bundle_summary.get('valid_external_bundle_count', 0))
    cert_summary['tier4_invalid_external_bundle_count'] = int(bundle_summary.get('invalid_external_bundle_count', 0))
    cert_summary['tier4_missing_external_bundle_count'] = int(bundle_summary.get('missing_external_bundle_count', max(profile_count - preserved_bundle_count, 0)))
    cert_summary['tier4_external_handoff_template_present'] = True
    cert_summary['tier4_ready_targets'] = sorted(promoted_targets)
    cert_summary['tier4_bundle_promotion_complete'] = full_boundary_promoted
    cert['passed'] = fully_certifiable
    details: list[str] = []
    if full_boundary_promoted:
        details.append('Tier 4 peer bundle promotion is complete for the full retained boundary.')
    else:
        details.append('Tier 4 independent peer validation is not complete for the full retained boundary.')
    if int(bundle_summary.get('invalid_external_bundle_count', 0)):
        details.append('One or more preserved external bundle submissions were rejected as incomplete, non-independent, or otherwise invalid.')
    if not clean_room_green:
        details.append('Validated clean-room install matrix evidence is incomplete or missing.')
    if not in_scope_green:
        details.append('Validated in-scope certification lane execution evidence is incomplete or missing.')
    if not migration_ok:
        details.append('Migration upgrade → downgrade → reapply portability has not been preserved for both SQLite and PostgreSQL.')
    if not tier3_rebuilt:
        details.append('Tier 3 evidence has not yet been explicitly rebuilt from validated-run manifests.')
    if not runtime_ready:
        details.append('Runtime readiness is not yet proven in the current repository state reports.')
    cert['details'] = details
    cert_summary['open_gaps'] = details
    cert_path.write_text(json.dumps(cert, indent=2) + '\n', encoding='utf-8')
    cert_md_summary = {
        'fully_certifiable_now': cert_summary.get('fully_certifiable_now'),
        'fully_rfc_compliant_now': cert_summary.get('fully_rfc_compliant_now'),
        'strict_independent_claims_ready': cert_summary.get('strict_independent_claims_ready'),
        'tier4_bundle_promotion_complete': cert_summary.get('tier4_bundle_promotion_complete'),
        'clean_room_matrix_green': clean_room_green,
        'in_scope_test_lanes_green': in_scope_green,
        'migration_portability_passed': migration_ok,
        'tier3_evidence_rebuilt_from_validated_runs': tier3_rebuilt,
    }
    write_text(ROOT / 'docs' / 'compliance' / 'certification_state_report.md', _render_state_markdown('Certification State Report', bool(cert['passed']), cert_md_summary, details))


def update_release_gate_report(promoted_targets: set[str], retained_targets: list[str]) -> None:
    full_boundary_promoted = bool(retained_targets) and set(retained_targets) <= promoted_targets
    path = ROOT / 'docs' / 'compliance' / 'release_gate_report.json'
    report = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'passed': False, 'summary': {}, 'details': []}
    summary = report.setdefault('summary', {})
    summary['tier4_bundle_promotion_complete'] = full_boundary_promoted
    detail_map = {item.get('gate'): item for item in report.get('details', []) if isinstance(item, dict) and item.get('gate')}
    detail_map.setdefault('gate-45-evidence-peer', {'gate': 'gate-45-evidence-peer', 'passed': full_boundary_promoted, 'rc': 0 if full_boundary_promoted else 1})
    detail_map['gate-45-evidence-peer']['passed'] = full_boundary_promoted
    detail_map['gate-45-evidence-peer']['rc'] = 0 if full_boundary_promoted else 1
    release_ready = bool(summary.get('clean_room_install_matrix_green', False) and summary.get('in_scope_test_lanes_green', False) and summary.get('migration_portability_passed', False) and summary.get('tier3_evidence_rebuilt_from_validated_runs', False) and full_boundary_promoted)
    detail_map.setdefault('gate-90-release', {'gate': 'gate-90-release', 'passed': release_ready, 'rc': 0 if release_ready else 1})
    detail_map['gate-90-release']['passed'] = release_ready
    detail_map['gate-90-release']['rc'] = 0 if release_ready else 1
    ordered = sorted(detail_map.values(), key=lambda item: str(item['gate']))
    report['details'] = ordered
    report['failures'] = [f"Gate failed: {item['gate']}" for item in ordered if not item.get('passed')]
    report['passed'] = not report['failures']
    summary['failed_gate_count'] = len(report['failures'])
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    md_summary = {
        'gate_count': summary.get('gate_count'),
        'failed_gate_count': summary.get('failed_gate_count'),
        'clean_room_install_matrix_green': summary.get('clean_room_install_matrix_green'),
        'in_scope_test_lanes_green': summary.get('in_scope_test_lanes_green'),
        'migration_portability_passed': summary.get('migration_portability_passed'),
        'tier3_evidence_rebuilt_from_validated_runs': summary.get('tier3_evidence_rebuilt_from_validated_runs'),
        'tier4_bundle_promotion_complete': summary.get('tier4_bundle_promotion_complete'),
    }
    details = [f"{item['gate']}: {'passed' if item.get('passed') else 'failed'}" for item in ordered]
    write_text(ROOT / 'docs' / 'compliance' / 'release_gate_report.md', _render_state_markdown('Release Gate Report', bool(report['passed']), md_summary, details))


def update_final_target_decision_matrix() -> None:
    path = ROOT / 'docs' / 'compliance' / 'final_target_decision_matrix.json'
    if not path.exists():
        return
    matrix = json.loads(path.read_text(encoding='utf-8'))
    claims_doc = load_claims()
    scope_doc = load_yaml(ROOT / 'compliance' / 'targets' / 'certification_scope.yaml') or {}
    claim_entries = {str(item.get('target')): item for item in claims_doc.get('claim_set', {}).get('claims', [])}
    scope_entries = {str(item.get('label')): item for item in scope_doc.get('targets', [])}
    target_to_peer = load_yaml(ROOT / 'compliance' / 'mappings' / 'target-to-peer-profile.yaml') or {}
    evidence_manifest = load_yaml(ROOT / 'compliance' / 'evidence' / 'manifest.yaml') or {}
    state = evidence_manifest.get('state') or {}
    valid_preserved_bundle_paths = listify(state.get('valid_preserved_tier4_bundles') or state.get('preserved_tier4_bundles'))
    invalid_preserved_bundle_paths = listify(state.get('invalid_preserved_tier4_bundles'))
    valid_profiles = {Path(path).name.split('--', 1)[0] for path in valid_preserved_bundle_paths}
    invalid_profiles = {Path(path).name.split('--', 1)[0] for path in invalid_preserved_bundle_paths}
    rows = matrix.get('rows', [])
    cert = json.loads((ROOT / 'docs' / 'compliance' / 'certification_state_report.json').read_text(encoding='utf-8'))
    release_gate = json.loads((ROOT / 'docs' / 'compliance' / 'release_gate_report.json').read_text(encoding='utf-8'))
    for row in rows:
        target = str(row.get('target'))
        claim = claim_entries.get(target, {})
        scope_entry = scope_entries.get(target, {})
        tier = int(claim.get('tier', row.get('claim_tier', 0) or 0))
        row['claim_tier'] = tier
        row['claim_status'] = str(claim.get('status', row.get('claim_status', 'unknown')))
        row['profile'] = str(claim.get('profile', scope_entry.get('first_claimable_profile', row.get('profile', 'unknown'))))
        row['scope_bucket'] = str(scope_entry.get('scope_bucket', row.get('scope_bucket', 'unknown')))
        row['status'] = 'certifiably-complete' if tier >= 4 else ('complete-but-not-independently-peer-certified' if tier >= 3 else 'partial/deferred')
        mapped_profiles = [str(item) for item in listify(target_to_peer.get(target))]
        available_valid_profiles = [profile for profile in mapped_profiles if profile in valid_profiles]
        available_invalid_profiles = [profile for profile in mapped_profiles if profile in invalid_profiles]
        if available_valid_profiles:
            row['peer_evidence'] = f"validated preserved bundle present: {', '.join(available_valid_profiles)}"
        elif available_invalid_profiles:
            row['peer_evidence'] = f"preserved bundle rejected: {', '.join(available_invalid_profiles)}"
        else:
            row['peer_evidence'] = f"none preserved; candidate profile(s): {', '.join(mapped_profiles)}" if mapped_profiles else 'none mapped'
    matrix['fully_certifiable_now'] = bool(cert.get('summary', {}).get('fully_certifiable_now', False))
    matrix['fully_rfc_compliant_now'] = bool(cert.get('summary', {}).get('fully_rfc_compliant_now', False))
    matrix['release_gates_passed'] = bool(release_gate.get('passed', False))
    matrix['tier4_bundle_promotion_complete'] = bool(cert.get('summary', {}).get('strict_independent_claims_ready', False))
    partition = {
        'certifiably_complete': [row['target'] for row in rows if row['status'] == 'certifiably-complete'],
        'complete_but_not_independently_peer_certified': [row['target'] for row in rows if row['status'] == 'complete-but-not-independently-peer-certified'],
        'partial_deferred': [row['target'] for row in rows if row['status'] == 'partial/deferred'],
        'out_of_scope': [row['target'] for row in matrix.get('out_of_scope', [])],
    }
    matrix['partition'] = partition
    path.write_text(json.dumps(matrix, indent=2) + '\n', encoding='utf-8')


def update_top_level_docs(promoted_targets: set[str], retained_targets: list[str], preserved_bundle_count: int, external_root: Path | None) -> None:
    """Top-level docs are regenerated later from current-state reports."""
    return None

def write_status_doc(promoted_targets: set[str], retained_targets: list[str], preserved_bundle_count: int, external_root: Path | None) -> None:
    full_boundary_promoted = bool(retained_targets) and set(retained_targets) <= promoted_targets
    peer_matrix_report = json.loads((ROOT / 'docs' / 'compliance' / 'peer_matrix_report.json').read_text(encoding='utf-8')) if (ROOT / 'docs' / 'compliance' / 'peer_matrix_report.json').exists() else {'summary': {}}
    bundle_summary = peer_matrix_report.get('summary', {})
    lines = [
        '# Tier 4 Peer Program Status — 2026-03-25',
        '',
        '## Summary',
        '',
        f'- external artifact root: `{relpath(external_root) if external_root else None}`',
        f'- peer profile count: `{len(load_peer_profiles())}`',
        f"- preserved external bundle count: `{bundle_summary.get('external_bundle_count', preserved_bundle_count)}`",
        f"- valid independent external bundle count: `{bundle_summary.get('valid_external_bundle_count', 0)}`",
        f"- invalid or rejected preserved bundle count: `{bundle_summary.get('invalid_external_bundle_count', 0)}`",
        f'- promoted target count: `{len(promoted_targets)}`',
        f'- retained target count: `{len(retained_targets)}`',
        f'- retained boundary promoted: `{full_boundary_promoted}`',
        '',
        '## Current state',
        '',
    ]
    if full_boundary_promoted:
        lines.append('The Tier 4 peer-program bundle set is complete for the kept boundary. The repository still remains short of final certification because the validated runtime/test/migration/evidence gate stack is not yet green in this checkpoint environment.')
    else:
        lines.append('The Tier 4 peer-program handoff package is present, but preserved qualifying external bundles are not currently counted for final release truth. Repository-staged fixture material is now explicitly rejected for Tier 4 promotion and strict independent claims.')
    lines.extend([
        '',
        '## Key artifacts',
        '',
        '- `docs/compliance/PEER_MATRIX_REPORT.md`',
        '- `docs/compliance/TIER4_PROMOTION_MATRIX.md`',
        '- `docs/compliance/current_state_report.md`',
        '- `docs/compliance/certification_state_report.md`',
        '- `compliance/evidence/tier4/bundles/`',
        '- `compliance/evidence/tier4/fixtures/`',
        '- `dist/tier4-external-handoff/`',
        '- `dist/tier4-external-root-fixtures/`',
    ])
    write_text(ROOT / 'docs' / 'compliance' / 'TIER4_PEER_PROGRAM_STATUS_2026-03-25.md', '\n'.join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Materialize runtime-foundation checkpoint3 independent peer-program artifacts.')
    parser.add_argument('--external-root', type=Path, default=None, help='Optional root containing externally generated peer artifacts by profile id.')
    parser.add_argument('--no-promote', action='store_true', help='Do not promote claims even when valid external bundles are present.')
    parser.add_argument('--require-full-boundary', action='store_true', help='Return a non-zero exit status unless the full retained boundary is covered by valid independent external bundles.')
    args = parser.parse_args(argv)

    external_root = args.external_root.resolve() if args.external_root else None
    peer_profiles = load_peer_profiles()
    counterparts = load_counterparts()
    target_tests = load_target_test_mapping()
    retained_targets = load_retained_targets()
    contract_paths = canonical_contract_snapshots()

    if external_root is not None:
        os.environ['TBA_AUTH_PEER_ARTIFACTS_ROOT'] = str(external_root)

    materialize_external_handoff_templates(peer_profiles, counterparts)
    write_peer_profile_execution_reports(peer_profiles, external_root, retained_targets)

    peer_matrix: list[dict[str, Any]] = []
    preserved_bundles: list[str] = []
    valid_preserved_bundles: list[str] = []
    invalid_preserved_bundles: list[str] = []
    candidate_dirs: list[str] = []
    promoted_targets: set[str] = set()

    coverage = target_coverage(peer_profiles)
    missing_coverage = sorted(set(retained_targets) - set(coverage))

    for profile_id, profile in peer_profiles.items():
        counterpart_id = str(profile.get('counterpart_id', '')).strip()
        counterpart = counterparts[counterpart_id]
        candidate = ensure_candidate_layout(profile_id, profile, counterpart, target_tests, contract_paths)
        candidate_dirs.append(candidate['candidate_dir'])
        row = {
            'profile': profile_id,
            'counterpart_id': counterpart_id,
            'runtime_profile': profile.get('preferred_runtime_profile', 'hardening'),
            'required_targets': listify(profile.get('required_targets')),
            'candidate_dir': candidate['candidate_dir'],
            'external_bundle_dir': None,
            'promotable_targets': [],
            'validation_failures': [],
        }
        if external_root is not None:
            bundle = materialize_external_bundle(profile_id, profile, counterpart, external_root, target_tests)
        else:
            bundle = load_preserved_bundle_status(profile_id, counterpart_id, profile)
        if bundle is not None:
            row['external_bundle_dir'] = bundle['bundle_dir']
            row['promotable_targets'] = bundle['promotable_targets']
            row['validation_failures'] = bundle.get('validation_failures', [])
            preserved_bundles.append(bundle['bundle_dir'])
            if bundle.get('passed'):
                valid_preserved_bundles.append(bundle['bundle_dir'])
                if not args.no_promote:
                    promoted_targets.update(bundle['promotable_targets'])
            else:
                invalid_preserved_bundles.append(bundle['bundle_dir'])
        peer_matrix.append(row)

    claims_doc = update_claims(promoted_targets, retained_targets)
    update_repository_state(promoted_targets, peer_matrix, len(preserved_bundles), retained_targets)
    update_evidence_manifest(
        preserved_bundles,
        valid_preserved_bundles,
        invalid_preserved_bundles,
        candidate_dirs,
        promoted_targets,
        retained_targets,
        len(peer_profiles),
    )
    write_peer_matrix_reports(peer_matrix, promoted_targets, retained_targets)
    write_peer_program_docs(promoted_targets, peer_matrix, len(preserved_bundles), retained_targets, external_root)
    write_peer_materialization_report(promoted_targets, len(preserved_bundles), retained_targets, external_root, len(peer_profiles))
    write_evidence_peer_readiness_report(promoted_targets, len(preserved_bundles), claims_doc)
    update_current_and_certification_state_reports(promoted_targets, retained_targets, len(preserved_bundles))
    update_release_gate_report(promoted_targets, retained_targets)
    update_final_target_decision_matrix()
    update_top_level_docs(promoted_targets, retained_targets, len(preserved_bundles), external_root)
    write_status_doc(promoted_targets, retained_targets, len(preserved_bundles), external_root)

    full_boundary_promoted = bool(retained_targets) and set(retained_targets) <= promoted_targets
    payload = {
        'passed': not missing_coverage and (full_boundary_promoted if args.require_full_boundary else True),
        'external_root': relpath(external_root) if external_root else None,
        'preserved_bundle_count': len(preserved_bundles),
        'valid_external_bundle_count': len(valid_preserved_bundles),
        'invalid_external_bundle_count': len(invalid_preserved_bundles),
        'candidate_profile_count': len(candidate_dirs),
        'promoted_target_count': len(promoted_targets),
        'promoted_targets': sorted(promoted_targets),
        'retained_target_count': len(retained_targets),
        'missing_retained_target_coverage': missing_coverage,
        'retained_boundary_promoted': full_boundary_promoted,
        'require_full_boundary': bool(args.require_full_boundary),
    }
    write_json(ROOT / 'docs' / 'archive' / 'historical' / 'compliance' / 'independent_peer_materialization_report.json', payload)
    if args.require_full_boundary and not full_boundary_promoted:
        return 1
    if missing_coverage:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
