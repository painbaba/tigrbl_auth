from __future__ import annotations

def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _error_manifest(exc: BaseException) -> dict[str, str]:
    return {"type": exc.__class__.__name__, "message": str(exc)}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _trim_probe_output(value: str | None, *, limit: int = 1000) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def _extract_json_payload(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = text.strip()
    if not cleaned:
        return None
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None


def _surface_probe_skipped(message: str) -> dict[str, Any]:
    return {
        "executed": False,
        "passed": False,
        "message": message,
        "endpoint_count": 0,
        "passed_count": 0,
        "failed_count": 0,
        "probes": [],
    }


def _command_probe_skipped(command: str, message: str) -> dict[str, Any]:
    return {
        "passed": False,
        "executed": False,
        "command": command,
        "message": message,
    }


def _validate_surface_response(name: str, path: str, status_code: int, payload: Any) -> tuple[bool, str]:
    if status_code != 200:
        return False, f"Expected HTTP 200 from `{path}`, received `{status_code}`."
    if name == "openid-configuration":
        if not isinstance(payload, dict):
            return False, "OpenID configuration response is not a JSON object."
        if not payload.get("issuer") or not payload.get("jwks_uri"):
            return False, "OpenID configuration is missing `issuer` or `jwks_uri`."
        return True, "OpenID discovery document is available."
    if name == "oauth-authorization-server":
        if not isinstance(payload, dict):
            return False, "Authorization-server metadata response is not a JSON object."
        if not payload.get("issuer") or not payload.get("jwks_uri"):
            return False, "Authorization-server metadata is missing `issuer` or `jwks_uri`."
        return True, "OAuth authorization-server metadata is available."
    if name == "oauth-protected-resource":
        if not isinstance(payload, dict):
            return False, "Protected-resource metadata response is not a JSON object."
        if not payload.get("authorization_servers") and not payload.get("resource") and not payload.get("jwks_uri"):
            return False, "Protected-resource metadata is missing expected identifying fields."
        return True, "OAuth protected-resource metadata is available."
    if name == "jwks":
        keys = payload.get("keys") if isinstance(payload, dict) else None
        if not isinstance(keys, list):
            return False, "JWKS response does not contain a `keys` array."
        return True, "JWKS document is available."
    if name == "public-contract":
        if not isinstance(payload, dict):
            return False, "OpenAPI response is not a JSON object."
        if not payload.get("openapi"):
            return False, "OpenAPI document is missing the `openapi` version field."
        paths = payload.get("paths") if isinstance(payload.get("paths"), dict) else {}
        required_paths = {"/.well-known/openid-configuration", "/.well-known/jwks.json"}
        if not required_paths.issubset(set(paths)):
            return False, "OpenAPI document is missing the public discovery/JWKS routes."
        return True, "Public contract endpoint is available."
    return True, f"Probe for `{path}` succeeded."


async def _probe_http_surface_endpoints_async(app: Any, deployment: Any | None = None) -> dict[str, Any]:
    try:
        from httpx import ASGITransport, AsyncClient
    except Exception as exc:  # pragma: no cover - optional import safety
        return _surface_probe_skipped(f"HTTP probe transport unavailable: {exc}")

    probes: list[dict[str, Any]] = []
    targets = _surface_probe_targets(app=app, deployment=deployment)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://runtime-probe") as client:
        for item in targets:
            name = str(item["name"])
            path = str(item["path"])
            try:
                response = await client.get(path)
                try:
                    payload = response.json()
                except ValueError:
                    payload = None
                passed, message = _validate_surface_response(name, path, int(response.status_code), payload)
                probes.append(
                    HttpEndpointProbeResult(
                        name=name,
                        path=path,
                        passed=passed,
                        message=message,
                        status_code=int(response.status_code),
                    ).to_manifest()
                )
            except Exception as exc:  # pragma: no cover - depends on runtime stack availability
                probes.append(
                    HttpEndpointProbeResult(
                        name=name,
                        path=path,
                        passed=False,
                        message=str(exc),
                        status_code=None,
                        error_type=exc.__class__.__name__,
                    ).to_manifest()
                )
    passed_count = sum(1 for item in probes if item.get("passed"))
    failed_count = len(probes) - passed_count
    return {
        "executed": True,
        "passed": failed_count == 0,
        "message": "Runtime HTTP surface probes completed successfully." if failed_count == 0 else "One or more runtime HTTP surface probes failed.",
        "endpoint_count": len(probes),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "probes": probes,
    }


def probe_http_surface_endpoints(*, app: Any, deployment: Any | None = None) -> dict[str, Any]:
    return asyncio.run(_probe_http_surface_endpoints_async(app, deployment=deployment))


def probe_runner_serve_check(
    repo_root: Path,
    runner: str,
    *,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    display_command = f"tba-auth serve --repo-root {repo_root} --server {runner} --format json --check"
    script = shutil.which("tba-auth")
    if script:
        argv = [script, "serve", "--repo-root", str(repo_root), "--server", runner, "--format", "json", "--check"]
    else:
        argv = [sys.executable, "-m", "tba_cli_identity.cli.main", "serve", "--repo-root", str(repo_root), "--server", runner, "--format", "json", "--check"]
    env = os.environ.copy()
    env["TBA_AUTH_SKIP_EXECUTION_PROBES"] = "1"
    try:
        result = subprocess.run(
            argv,
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - subprocess environment dependent
        return CommandProbeResult(
            passed=False,
            executed=True,
            command=display_command,
            message=str(exc),
            error_type=exc.__class__.__name__,
        ).to_manifest()

    payload = _extract_json_payload(result.stdout)
    launch_ready = None
    message = "serve --check completed."
    if payload is not None:
        launch_ready = payload.get("launch_ready")
        message = str(
            payload.get("launch_blocked_reason")
            or payload.get("application_probe", {}).get("message")
            or payload.get("selected_runner_profile", {}).get("status")
            or message
        )
    passed = bool(result.returncode == 0 and launch_ready is True)
    return CommandProbeResult(
        passed=passed,
        executed=True,
        command=display_command,
        message=message,
        exit_code=int(result.returncode),
        launch_ready=bool(launch_ready) if launch_ready is not None else None,
        stdout=_trim_probe_output(result.stdout),
        stderr=_trim_probe_output(result.stderr),
    ).to_manifest()


def probe_application_factory(*, deployment: Any, settings_obj: object | None = None) -> tuple[ApplicationProbeResult, Any | None]:
    try:
        factories = entry_points(group="tba_auth.app_factories", name="default")
        if len(factories) != 1:
            raise RuntimeError("Install tba-app-backend-core to provide one default app factory.")
        factory = next(iter(factories))
        app = factory.load()(settings_obj, deployment=deployment)
    except Exception as exc:  # pragma: no cover - exercised via checkpoint environment and monkeypatched tests
        return (
            ApplicationProbeResult(
                passed=False,
                app_factory="unbound",
                message=str(exc),
                error_type=exc.__class__.__name__,
            ),
            None,
        )
    active_targets = len(getattr(deployment, "active_targets", []) or [])
    active_routes = len(getattr(deployment, "active_routes", []) or [])
    return (
        ApplicationProbeResult(
            passed=True,
            app_factory=factory.value.replace(":", "."),
            message=f"Application factory materialized successfully with {active_routes} active routes and {active_targets} active targets.",
            error_type=None,
        ),
        app,
    )


def build_runner_profile_report(
    repo_root: Path,
    *,
    deployment: Any,
    environment: str = "development",
    host: str = "127.0.0.1",
    port: int = 8000,
    workers: int = 1,
    access_log: bool = True,
    lifespan: str = "auto",
    graceful_timeout: int = 30,
    enable_execution_probes: bool | None = None,
    report_mode: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    resolved_report_mode = _runtime_report_mode(repo_root, report_mode)
    if resolved_report_mode == "validated-runs":
        return build_validated_runner_profile_report(repo_root, deployment=deployment)
    if enable_execution_probes is None:
        enable_execution_probes = os.environ.get("TBA_AUTH_SKIP_EXECUTION_PROBES", "").strip().lower() not in {"1", "true", "yes", "on"}
    app_probe, app = probe_application_factory(deployment=deployment)
    if app_probe.passed and enable_execution_probes:
        surface_probe = probe_http_surface_endpoints(app=app, deployment=deployment)
    elif not app_probe.passed:
        surface_probe = _surface_probe_skipped("Skipped because the application factory did not materialize in this environment.")
    else:
        surface_probe = _surface_probe_skipped("Execution probes were disabled for this invocation.")
    support_manifest = _build_runner_support_manifest(repo_root)
    hash_matrix = build_runtime_hash_matrix(
        deployment=deployment,
        environment=environment,
        host=host,
        port=port,
        workers=workers,
        access_log=access_log,
        lifespan=lifespan,
        graceful_timeout=graceful_timeout,
    )
    profiles: list[dict[str, Any]] = []
    ready_count = 0
    missing_count = 0
    invalid_count = 0
    for adapter in iter_runner_adapters():
        plan = build_runtime_plan(
            deployment=deployment,
            runner=adapter.name,
            environment=environment,
            host=host,
            port=port,
            workers=workers,
            access_log=access_log,
            lifespan=lifespan,
            graceful_timeout=graceful_timeout,
        )
        diagnostics = [item.to_manifest() for item in plan.diagnostics_report]
        installed = adapter.is_available()
        support = dict((support_manifest.get("profiles") or {}).get(adapter.name, {}))
        serve_command = f"tba-auth serve --repo-root {repo_root} --server {adapter.name} --format json --check"
        if enable_execution_probes and installed and app_probe.passed and surface_probe.get("passed", False):
            serve_check = probe_runner_serve_check(repo_root, adapter.name)
        elif not enable_execution_probes:
            serve_check = _command_probe_skipped(serve_command, "Execution probes were disabled for this invocation.")
        elif not installed:
            serve_check = _command_probe_skipped(serve_command, "Skipped because the runner is not installed in this environment.")
        elif not app_probe.passed:
            serve_check = _command_probe_skipped(serve_command, "Skipped because the application factory did not materialize in this environment.")
        else:
            serve_check = _command_probe_skipped(serve_command, "Skipped because runtime HTTP surface probes failed.")

        if not installed:
            status = "missing"
            missing_count += 1
        elif (
            not app_probe.passed
            or any(item["level"] == "error" for item in diagnostics)
            or (enable_execution_probes and not surface_probe.get("passed", False))
            or (enable_execution_probes and not serve_check.get("passed", False))
        ):
            status = "invalid"
            invalid_count += 1
        else:
            status = "ready"
            ready_count += 1
        profiles.append(
            {
                "name": adapter.name,
                "display_name": adapter.display_name,
                "status": status,
                "installed": installed,
                "available_module": adapter.available_module_name(),
                "capabilities": [item.to_manifest() for item in adapter.capabilities],
                "flag_metadata": [item.to_manifest() for item in adapter.flag_metadata],
                "diagnostics": diagnostics,
                "application_hash": hash_matrix[adapter.name]["application_hash"],
                "runtime_hash": hash_matrix[adapter.name]["runtime_hash"],
                "serve_check": serve_check,
                **support,
            }
        )
    placeholder_supported_runner_names = [item["name"] for item in profiles if item.get("placeholder_supported")]
    declared_ci_installable_runner_names = [item["name"] for item in profiles if item.get("declared_installable_from_repository")]
    serve_check_passed_count = sum(1 for item in profiles if item.get("serve_check", {}).get("passed"))
    execution_probe_complete = bool(
        enable_execution_probes
        and app_probe.passed
        and surface_probe.get("executed", False)
        and all(item.get("serve_check", {}).get("executed", False) for item in profiles if item.get("installed"))
    )
    return {
        "generated_at": _utc_timestamp(),
        "deployment_profile": deployment.profile,
        "report_mode": "live-probe",
        "application_probe": app_probe.to_manifest(),
        "surface_probe": surface_probe,
        "summary": {
            "runner_count": len(profiles),
            "ready_count": ready_count,
            "missing_count": missing_count,
            "invalid_count": invalid_count,
            "application_hash_invariant": len({item["application_hash"] for item in profiles}) == 1 if profiles else False,
            "pyproject_requires_python": support_manifest.get("requires_python"),
            "supported_python_versions": support_manifest.get("supported_python_versions", []),
            "placeholder_supported_runner_count": len(placeholder_supported_runner_names),
            "placeholder_supported_runner_names": placeholder_supported_runner_names,
            "declared_ci_installable_runner_count": len(declared_ci_installable_runner_names),
            "declared_ci_installable_runner_names": declared_ci_installable_runner_names,
            "declared_ci_install_probe_complete": len(declared_ci_installable_runner_names) == len(profiles),
            "execution_probes_enabled": bool(enable_execution_probes),
            "surface_probe_passed": bool(surface_probe.get("passed", False)),
            "surface_probe_endpoint_count": int(surface_probe.get("endpoint_count", 0)),
            "surface_probe_passed_count": int(surface_probe.get("passed_count", 0)),
            "surface_probe_failed_count": int(surface_probe.get("failed_count", 0)),
            "serve_check_passed_count": serve_check_passed_count,
            "execution_probe_complete": execution_probe_complete,
            "source_mode": "live-probe",
            "required_runtime_cell_count": len([version for cfg in RUNTIME_VALIDATION_GROUPS.values() for version in cfg["supported_python_versions"]]),
            "validated_runtime_cell_count": 0,
            "validated_runtime_cell_passed_count": 0,
            "validated_runtime_matrix_green": False,
            "validated_download_collection_present": False,
        },
        "profiles": profiles,
    }
