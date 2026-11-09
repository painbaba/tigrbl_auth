# Truth Chain

This manifest is a generated checkpoint projection derived from the SSOT authority policy.

- generated_at: `2026-11-09`
- final_release_ready: `False`
- checkpoint_only: `True`
- release_gates_passed: `True`
- final_release_gate_passed: `False`

## Source of truth

- `.ssot/registry.json`
- `.ssot/specs/SPEC-1052-ssot-document-authority.yaml`
- `docs/compliance/current_state_report.json`
- `docs/compliance/certification_state_report.json`
- `docs/compliance/release_gate_report.json`
- `docs/compliance/final_release_gate_report.json`
- `docs/compliance/non_rfc_status_report.json`

## Summary

- declared_claim_count: `48`
- tier_3_claim_count: `48`
- tier_4_claim_count: `0`
- validated_inventory_complete: `False`
- validated_runtime_matrix_green: `False`
- validated_test_lanes_green: `False`
- migration_portability_passed: `True`
- tier3_evidence_rebuilt_from_validated_runs: `False`
- fully_featured_package_boundary_now: `False`
- strict_independent_claims_ready: `False`
- fully_certifiable_now: `False`
- fully_rfc_compliant_now: `False`
- fully_non_rfc_spec_compliant_now: `False`
- release_gates_passed: `True`
- release_gate_count: `1`
- release_gate_failed_count: `0`
- final_release_gate_passed: `False`
- final_release_ready: `False`
- checkpoint_only: `True`
- target_profile_truth_reconciled_complete: `True`
- profile_scope_mismatch_set_empty: `True`
- clean_room_executor_matrix_declared_complete: `True`
- validated_manifest_identity_contract_installed: `True`
- claim_registry_canonical_complete: `True`
- fapi2_security_profile_declared_complete: `True`
- release_claims_machine_derivable: `True`
- core_targets_missing_from_feature_map: `0`
- extension_targets_missing_from_feature_map: `0`
- settings_backed_flags_missing_from_flag_map: `0`
- tier4_external_bundle_count: `16`
- tier4_valid_external_bundle_count: `0`
- tier4_invalid_external_bundle_count: `16`
- tier4_missing_external_bundle_count: `0`
- open_gaps: `['Tier 4 independent peer validation is not complete for the retained boundary.', 'The fill-in external handoff template package is not present for the full supported peer-profile set.', 'The peer-bundle completeness gate is not satisfied for the declared peer-profile set.', 'One or more supported peer profiles have incomplete or invalid preserved external evidence bundles.', 'The runtime validation stack now executes real app-factory, serve-check, and HTTP surface probes in the clean-room matrix, but successful execution across the supported interpreter/profile matrix is not yet preserved in the validated-run inventory.', 'Tigrcorn is now pinned and included in the clean-room matrix for Python 3.11/3.12, but preserved independent validation artifacts remain absent.', 'The runtime HTTP surface probe is not yet proven green across the preserved validated base-environment manifests.', 'The application factory is not yet proven materialized across the preserved validated base-environment manifests.', 'Real runtime execution probes are implemented in tox and CI, but the preserved validated runtime inventory does not yet cover the full kept-runner matrix.', 'Validated clean-room install matrix evidence is incomplete or missing.', 'Validated in-scope certification lane execution evidence is incomplete or missing.', 'Tier 3 evidence has not yet been explicitly rebuilt from validated-run manifests.', 'One or more operator-visible package capabilities still lacks end-to-end verification in the current environment.', 'At least one claim row is still missing a machine-derived certification proof binding.', 'Release evidence can now be built only from a clean checkout, and the current workspace is dirty.']`
- final_release_failures: `['Validated artifact inventory is below the required 14 runtime + 15 test lanes + 1 migration threshold.', 'In-scope certification test lanes are not green from validated-run evidence.']`
- final_release_warnings: `['Tier 4 bundle promotion is not complete for the retained boundary.']`
- explicitly_deauthorized_current_adjacent_doc_count: `7`

## Explicitly deauthorized current-adjacent docs

- `docs/compliance/BOUNDARY_FREEZE_DECISION_2026-03-26.md`
- `docs/compliance/CLEAN_ROOM_EXECUTOR_AND_EVIDENCE_CHECKPOINT_2026-03-27.md`
- `docs/compliance/PEER_MATRIX_REPORT.md`
- `docs/compliance/TIER4_PROMOTION_MATRIX.md`
- `docs/compliance/CERTIFIABLE_COMPLETION_PLAN_2026-03-26.md`
- `docs/compliance/CERTIFIABLE_DELIVERY_PLAN_2026-03-27.md`
- `docs/compliance/TARGET_REALITY_MATRIX.md`
