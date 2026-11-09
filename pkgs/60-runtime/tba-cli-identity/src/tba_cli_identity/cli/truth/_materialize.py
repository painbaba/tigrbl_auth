from __future__ import annotations

def render_current_state_markdown(truth: dict[str, Any]) -> str:
    summary = truth["summary"]
    lines = [
        "# CURRENT_STATE",
        "",
        "## Summary",
        "",
        "This repository is governed by the SSOT authority policy in `.ssot/specs/SPEC-1052-ssot-document-authority.yaml`, projected through `docs/compliance/truth_chain.json`.",
        "",
        (
            "The current package state is certifiably fully featured, certifiably fully RFC/spec compliant, and ready for a final certified release."
            if summary["final_release_ready"]
            else "The current package state is a blocked certification checkpoint. It is not certifiably fully featured and it is not certifiably fully RFC/spec compliant."
        ),
        "",
        "## Current generated state",
        "",
        f"- declared in-scope claim count: `{summary['declared_claim_count']}`",
        f"- Tier 3 claim count: `{summary['tier_3_claim_count']}`",
        f"- Tier 4 claim count: `{summary['tier_4_claim_count']}`",
        f"- strict independent claims ready: `{summary['strict_independent_claims_ready']}`",
        f"- fully certifiable now: `{summary['fully_certifiable_now']}`",
        f"- fully RFC/spec compliant now: `{summary['fully_rfc_compliant_now']}`",
        f"- fully non-RFC spec/standard compliant now: `{summary['fully_non_rfc_spec_compliant_now']}`",
        f"- release gates passed: `{summary['release_gates_passed']}`",
        f"- final release gate passed: `{summary['final_release_gate_passed']}`",
        f"- final release ready: `{summary['final_release_ready']}`",
        f"- checkpoint only: `{summary['checkpoint_only']}`",
        f"- target/profile truth reconciled complete: `{summary['target_profile_truth_reconciled_complete']}`",
        f"- profile-scope mismatch set empty: `{summary['profile_scope_mismatch_set_empty']}`",
        f"- clean-room executor matrix declared complete: `{summary['clean_room_executor_matrix_declared_complete']}`",
        f"- validated manifest identity contract installed: `{summary['validated_manifest_identity_contract_installed']}`",
        f"- claim registry canonical complete: `{summary['claim_registry_canonical_complete']}`",
        f"- FAPI 2.0 security profile declared complete: `{summary['fapi2_security_profile_declared_complete']}`",
        f"- release claims machine-derivable: `{summary['release_claims_machine_derivable']}`",
        f"- core targets missing from feature map: `{summary['core_targets_missing_from_feature_map']}`",
        f"- extension targets missing from feature map: `{summary['extension_targets_missing_from_feature_map']}`",
        f"- settings-backed flags missing from flag map: `{summary['settings_backed_flags_missing_from_flag_map']}`",
        f"- validated inventory complete: `{summary['validated_inventory_complete']}`",
        f"- validated runtime matrix green: `{summary['validated_runtime_matrix_green']}`",
        f"- validated test lanes green: `{summary['validated_test_lanes_green']}`",
        f"- migration portability passed: `{summary['migration_portability_passed']}`",
        f"- Tier 4 missing external bundle count: `{summary['tier4_missing_external_bundle_count']}`",
        "",
        "## Key artifacts",
        "",
        "- `docs/compliance/truth_chain.md`",
        "- `docs/compliance/current_state_report.md`",
        "- `docs/compliance/certification_state_report.md`",
        "- `docs/compliance/release_gate_report.md`",
        "- `docs/compliance/final_release_gate_report.md`",
        "- `docs/compliance/RELEASE_DECISION_RECORD.md`",
        "- `docs/compliance/FINAL_RELEASE_STATUS_2026-03-25.md`",
        "",
    ]
    return "\n".join(lines)


def render_certification_status_markdown(truth: dict[str, Any]) -> str:
    summary = truth["summary"]
    lines = [
        "# CERTIFICATION_STATUS",
        "",
        "## Honest status",
        "",
        f"- fully_certifiable_now: `{summary['fully_certifiable_now']}`",
        f"- fully_rfc_compliant_now: `{summary['fully_rfc_compliant_now']}`",
        f"- fully_non_rfc_spec_compliant_now: `{summary['fully_non_rfc_spec_compliant_now']}`",
        f"- strict_independent_claims_ready: `{summary['strict_independent_claims_ready']}`",
        f"- release_gates_passed: `{summary['release_gates_passed']}`",
        f"- final_release_gate_passed: `{summary['final_release_gate_passed']}`",
        f"- final_release_ready: `{summary['final_release_ready']}`",
        f"- target_profile_truth_reconciled_complete: `{summary['target_profile_truth_reconciled_complete']}`",
        f"- profile_scope_mismatch_set_empty: `{summary['profile_scope_mismatch_set_empty']}`",
        f"- validated_runtime_matrix_green: `{summary['validated_runtime_matrix_green']}`",
        f"- validated_test_lanes_green: `{summary['validated_test_lanes_green']}`",
        f"- migration_portability_passed: `{summary['migration_portability_passed']}`",
        f"- claim_registry_canonical_complete: `{summary['claim_registry_canonical_complete']}`",
        f"- fapi2_security_profile_declared_complete: `{summary['fapi2_security_profile_declared_complete']}`",
        f"- release_claims_machine_derivable: `{summary['release_claims_machine_derivable']}`",
        f"- core_targets_missing_from_feature_map: `{summary['core_targets_missing_from_feature_map']}`",
        f"- extension_targets_missing_from_feature_map: `{summary['extension_targets_missing_from_feature_map']}`",
        f"- settings_backed_flags_missing_from_flag_map: `{summary['settings_backed_flags_missing_from_flag_map']}`",
        "",
        "## Open gaps blocking final certification",
        "",
    ]
    if summary["open_gaps"]:
        lines.extend(f"- {item}" for item in summary["open_gaps"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Practical recommendation",
            "",
            (
                "This repository state can be labeled as a final certified release."
                if summary["final_release_ready"]
                else "This repository state must remain labeled as a checkpoint/candidate until Tier 4 independent validation and any remaining package-boundary gaps are closed."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_release_decision_record_markdown(truth: dict[str, Any]) -> str:
    summary = truth["summary"]
    lines = [
        "# Release Decision Record",
        "",
        "## Decision",
        "",
        (
            "Cut the final certified release."
            if summary["final_release_ready"]
            else "Do not cut a final certified release. Publish only a truthful checkpoint/candidate."
        ),
        "",
        "## Basis",
        "",
        f"- release_gates_passed: `{summary['release_gates_passed']}`",
        f"- release_gate_count: `{summary['release_gate_count']}`",
        f"- release_gate_failed_count: `{summary['release_gate_failed_count']}`",
        f"- final_release_gate_passed: `{summary['final_release_gate_passed']}`",
        f"- fully_certifiable_now: `{summary['fully_certifiable_now']}`",
        f"- fully_rfc_compliant_now: `{summary['fully_rfc_compliant_now']}`",
        f"- fully_non_rfc_spec_compliant_now: `{summary['fully_non_rfc_spec_compliant_now']}`",
        f"- strict_independent_claims_ready: `{summary['strict_independent_claims_ready']}`",
        f"- validated_runtime_matrix_green: `{summary['validated_runtime_matrix_green']}`",
        f"- validated_test_lanes_green: `{summary['validated_test_lanes_green']}`",
        f"- migration_portability_passed: `{summary['migration_portability_passed']}`",
        "",
        "## Explicitly deauthorized current-adjacent docs",
        "",
    ]
    if truth["explicitly_deauthorized_current_adjacent_docs"]:
        lines.extend(f"- `{item}`" for item in truth["explicitly_deauthorized_current_adjacent_docs"])
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def render_final_release_status_markdown(truth: dict[str, Any]) -> str:
    payload = _final_release_status_payload(truth)
    stem = _final_release_status_stem(Path("."))
    title = stem.replace("_", " ")
    lines = [f"# {title}", "", f"- Passed: `{payload['passed']}`", "", "## Summary", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in payload["summary"].items())
    lines.extend(["", "## Remaining blockers", ""])
    if payload["details"]:
        lines.extend(f"- {item}" for item in payload["details"])
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def render_compliance_current_state_markdown() -> str:
    return "\n".join(
        [
            "# Current State",
            "",
            "Use `.ssot/specs/SPEC-1052-ssot-document-authority.yaml` and SSOT-authored content under `.ssot/` as the authoritative source, with `docs/compliance/truth_chain.md` and the generated report set in this directory as projections.",
            "",
            "- authority_spec: `.ssot/specs/SPEC-1052-ssot-document-authority.yaml`",
            "- authority_roots: `.ssot/registry.json`, `.ssot/adr`, `.ssot/specs`",
            "- source_of_truth: `docs/compliance/truth_chain.json`",
            "- current_state_report: `docs/compliance/current_state_report.json`",
            "- release_gate_report: `docs/compliance/release_gate_report.json`",
            "- final_release_gate_report: `docs/compliance/final_release_gate_report.json`",
            "- release_decision_record: `docs/compliance/RELEASE_DECISION_RECORD.md`",
            "",
        ]
    )


def materialize_truth_chain(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    truth = build_truth_chain_payload(repo_root)
    repository_payload = build_repository_state_payload(repo_root, truth)
    final_status_json_path, final_status_md_path = _final_release_status_paths(repo_root)
    _write_yaml(repo_root / REPOSITORY_STATE_YAML, repository_payload)
    _write_json(repo_root / TRUTH_CHAIN_JSON, truth)
    _write_text(repo_root / TRUTH_CHAIN_MD, render_truth_chain_markdown(truth))
    _write_text(repo_root / ROOT_CURRENT_STATE, render_current_state_markdown(truth))
    _write_text(repo_root / ROOT_CERTIFICATION_STATUS, render_certification_status_markdown(truth))
    _write_text(repo_root / RELEASE_DECISION_RECORD_MD, render_release_decision_record_markdown(truth))
    final_status_payload = _final_release_status_payload(truth)
    _write_json(final_status_json_path, final_status_payload)
    title = final_status_json_path.stem.replace("_", " ")
    lines = [f"# {title}", "", f"- Passed: `{final_status_payload['passed']}`", "", "## Summary", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in final_status_payload["summary"].items())
    lines.extend(["", "## Remaining blockers", ""])
    if final_status_payload["details"]:
        lines.extend(f"- {item}" for item in final_status_payload["details"])
    else:
        lines.append("- none")
    lines.append("")
    _write_text(final_status_md_path, "\n".join(lines))
    _write_text(repo_root / "docs" / "compliance" / "current_state.md", render_compliance_current_state_markdown())
    return truth


def verify_truth_chain(
    repo_root: Path, *, mode: str = "all", use_recorded_date: bool = False
) -> dict[str, Any]:
    if use_recorded_date and mode != "current-state":
        raise ValueError("The recorded date is only supported for current-state verification.")
    repo_root = repo_root.resolve()
    truth = build_truth_chain_payload(repo_root)
    failures: list[str] = []
    warnings: list[str] = []
    if use_recorded_date:
        recorded_date = _read_json(repo_root / TRUTH_CHAIN_JSON).get("generated_at")
        try:
            snapshot_date = date.fromisoformat(recorded_date)
        except (TypeError, ValueError):
            failures.append("The recorded truth-chain date is missing or invalid.")
        else:
            if snapshot_date.isoformat() != recorded_date or snapshot_date > date.today():
                failures.append("The recorded truth-chain date is invalid.")
            else:
                truth["generated_at"] = recorded_date

    repository_payload = build_repository_state_payload(repo_root, truth)
    final_status_json_path, final_status_md_path = _final_release_status_paths(repo_root)

    expected_files: dict[str, str] = {}
    if mode in {"all", "current-state"}:
        expected_files[TRUTH_CHAIN_JSON] = json.dumps(truth, indent=2)
        expected_files[TRUTH_CHAIN_MD] = render_truth_chain_markdown(truth)
        expected_files[CURRENT_STATE_REPORT_MD] = _render_report_markdown("Current State Report", _read_json(repo_root / CURRENT_STATE_REPORT_JSON))
        expected_files[CERTIFICATION_STATE_REPORT_MD] = _render_report_markdown("Certification State Report", _read_json(repo_root / CERTIFICATION_STATE_REPORT_JSON))
        expected_files[ROOT_CURRENT_STATE] = render_current_state_markdown(truth)
        expected_files[ROOT_CERTIFICATION_STATUS] = render_certification_status_markdown(truth)
        expected_files["docs/compliance/current_state.md"] = render_compliance_current_state_markdown()
    if mode in {"all", "release-decision"}:
        expected_files[RELEASE_GATE_REPORT_MD] = _render_report_markdown("Release Gate Report", _read_json(repo_root / RELEASE_GATE_REPORT_JSON))
        expected_files[FINAL_RELEASE_GATE_REPORT_MD] = _render_report_markdown("Final Release Gate Report", _read_json(repo_root / FINAL_RELEASE_GATE_REPORT_JSON))
        expected_files[RELEASE_DECISION_RECORD_MD] = render_release_decision_record_markdown(truth)
        expected_files[str(final_status_json_path.relative_to(repo_root))] = json.dumps(_final_release_status_payload(truth), indent=2)
        title = final_status_json_path.stem.replace("_", " ")
        final_status_payload = _final_release_status_payload(truth)
        lines = [f"# {title}", "", f"- Passed: `{final_status_payload['passed']}`", "", "## Summary", ""]
        lines.extend(f"- {key}: `{value}`" for key, value in final_status_payload["summary"].items())
        lines.extend(["", "## Remaining blockers", ""])
        if final_status_payload["details"]:
            lines.extend(f"- {item}" for item in final_status_payload["details"])
        else:
            lines.append("- none")
        lines.append("")
        expected_files[str(final_status_md_path.relative_to(repo_root))] = "\n".join(lines)
    if mode in {"all", "repository-state"}:
        actual_repository_state = _read_yaml(repo_root / REPOSITORY_STATE_YAML)
        if actual_repository_state != repository_payload:
            failures.append(f"{REPOSITORY_STATE_YAML} does not match the generated truth-chain repository-state projection.")

    for rel_path, expected in expected_files.items():
        path = repo_root / rel_path
        actual = path.read_text(encoding="utf-8") if path.exists() else None
        if actual is None or _normalized_text(actual) != _normalized_text(expected):
            failures.append(f"{rel_path} does not match the generated truth-chain rendering.")

    return {
        "passed": not failures,
        "failures": failures,
        "warnings": warnings,
        "summary": {
            "mode": mode,
            "final_release_ready": bool(truth["summary"]["final_release_ready"]),
            "release_gates_passed": bool(truth["summary"]["release_gates_passed"]),
            "strict_independent_claims_ready": bool(truth["summary"]["strict_independent_claims_ready"]),
        },
    }
