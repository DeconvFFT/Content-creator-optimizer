import argparse
import asyncio
import hashlib
import ipaddress
import json
import os
import re
import shlex
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from pydantic import ValidationError

from all_about_llms.config import (
    MAX_RUST_VOICE_EDGE_BENCHMARK_SPEECH_FRAMES,
    PROJECT_ROOT,
    get_settings,
)
from all_about_llms.contracts import (
    AgentWorkerCycleRequest,
    AgentWorkerRunRequest,
    AutonomousStudioPassRequest,
    CockpitWalkthroughLedgerRequest,
    DistributionPackageRequest,
    ProviderReadinessResult,
    ProviderSmokeRunRequest,
    PublishReadinessResult,
    RealtimeVoiceTimingLedgerRequest,
    RunResumeRequest,
    RunState,
    RuntimeHealthLedgerRequest,
    RunSyncPulseRequest,
    VoiceRuntimeReadinessResult,
    WorkerSchedulerRunRequest,
)
from all_about_llms.local_provider_config import (
    LocalProviderConfigEnvName,
    validate_local_provider_config_value,
)
from all_about_llms.orchestration import (
    AgentWorker,
    AutonomousStudioPassWorkflow,
    CockpitWalkthroughLedgerWorkflow,
    DistributionPackageWorkflow,
    ProviderSmokeWorkflow,
    RealtimeVoiceTimingLedgerWorkflow,
    RunResumeWorkflow,
    RuntimeHealthLedgerWorkflow,
    RunSyncPulseWorkflow,
)
from all_about_llms.orchestration.blocker_credentials import (
    BLOCKER_CREDENTIAL_ENV_NAMES,
    BLOCKER_SECRET_FILE_ENV_NAMES,
    build_blocker_credential_snapshots,
)
from all_about_llms.orchestration.checkpointing import setup_postgres_checkpointer
from all_about_llms.orchestration.livekit_voice_timing_capture import (
    LiveKitVoiceTimingCaptureRequest,
    LiveKitVoiceTimingCaptureWorkflow,
)
from all_about_llms.orchestration.publish_readiness import (
    PUBLISH_CHANNEL_ALIASES,
    PUBLISH_CHANNEL_CREDENTIAL_ENVS,
)
from all_about_llms.orchestration.services import ContentWorkflowServices
from all_about_llms.providers.factory import (
    build_gemma_provider,
    build_realtime_provider,
    build_reranker_provider,
    build_search_provider,
)
from all_about_llms.providers.readiness import build_provider_readiness
from all_about_llms.storage import PostgresStore
from all_about_llms.storage.migrations import apply_foundation_schema, setup_durable_storage
from all_about_llms.voice_agent.benchmark import (
    VoiceEdgeBenchmarkConfig,
    load_wav_speech_fixture,
    run_voice_edge_benchmark,
    run_voice_edge_benchmark_corpus,
    run_voice_edge_threshold_sweep,
)
from all_about_llms.voice_agent.edge import (
    PersistentRustVoiceEdgeClient,
    RustVoiceEdgeHttpClient,
)
from all_about_llms.voice_agent.livekit_app import run_livekit_voice_agent_server

PROVIDER_PROOF_RECORD_TARGETS = [
    (
        "social_media_optimiser/01-work-tracking/"
        "Agent Studio Objective Completion Audit.md"
    ),
    "social_media_optimiser/wiki/ops/active-codex-context.md",
    (
        "system_design_vault/04-agent-studio-implications/"
        "agent-studio-objective-completion-audit.md"
    ),
]

PROVIDER_PROOF_CREDENTIAL_SETUP_REQUIREMENTS = {
    "provider-backed-live-voice-proof": [
        "configure OPENROUTER_API_KEY_FILE or OPENROUTER_API_KEY",
        "configure OPENROUTER_LIVEKIT_URL",
        "configure LIVEKIT_API_KEY_FILE or LIVEKIT_API_KEY",
        "configure LIVEKIT_API_SECRET_FILE or LIVEKIT_API_SECRET",
    ],
    "external-publication-proof": [
        "configure LINKEDIN_ACCESS_TOKEN_FILE or LINKEDIN_ACCESS_TOKEN",
    ],
}

PROVIDER_PROOF_CREDENTIAL_SETUP_COMMANDS = {
    "provider-backed-live-voice-proof": [
        "mkdir -p .secrets && chmod 700 .secrets",
        (
            ': "${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY first}" && '
            "umask 077 && printf '%s\\n' \"$OPENROUTER_API_KEY\" > "
            ".secrets/openrouter_api_key && chmod 600 .secrets/openrouter_api_key"
        ),
        (
            ': "${LIVEKIT_API_KEY:?set LIVEKIT_API_KEY first}" && '
            "umask 077 && printf '%s\\n' \"$LIVEKIT_API_KEY\" > "
            ".secrets/livekit_api_key && "
            "chmod 600 .secrets/livekit_api_key"
        ),
        (
            ': "${LIVEKIT_API_SECRET:?set LIVEKIT_API_SECRET first}" && '
            "umask 077 && printf '%s\\n' \"$LIVEKIT_API_SECRET\" > "
            ".secrets/livekit_api_secret && chmod 600 .secrets/livekit_api_secret"
        ),
        (
            ': "${OPENROUTER_LIVEKIT_URL:?set '
            'OPENROUTER_LIVEKIT_URL first}" && '
            ': "${LOCAL_PROVIDER_CONFIG_FILE:=.secrets/local_provider_config.json}" '
            "&& export OPENROUTER_LIVEKIT_URL LOCAL_PROVIDER_CONFIG_FILE && "
            "umask 077 && python3 -c 'import json, os, pathlib, sys; "
            "from urllib.parse import urlparse; "
            'names = ("OPENROUTER_LIVEKIT_URL",); '
            "values = {name: os.environ[name].strip() for name in names}; "
            "valid = lambda name, value: (lambda parsed, schemes: "
            "parsed.scheme in schemes and parsed.netloc and not "
            "(parsed.username or parsed.password or parsed.query or "
            'parsed.fragment))(urlparse(value), ({"ws", "wss", "http", '
            '"https"} if name == "OPENROUTER_LIVEKIT_URL" else '
            '{"http", "https"})); '
            "bad = [name for name, value in values.items() if not "
            "valid(name, value)]; "
            "bad and sys.exit(\"Invalid local provider config values: \" + "
            "\",\".join(bad)); "
            'path = pathlib.Path(os.environ["LOCAL_PROVIDER_CONFIG_FILE"]); '
            'ns = {"json": json, "path": path, "sys": sys}; '
            'exec("try:\\n existing = path.read_text(encoding=\\"utf-8\\") '
            'if path.exists() else \\"{}\\"\\n raw = json.loads(existing)\\n'
            'except Exception:\\n '
            'sys.exit(\\"Invalid existing LOCAL_PROVIDER_CONFIG_FILE\\")", ns); '
            'raw = ns["raw"]; '
            'isinstance(raw, dict) or sys.exit("Invalid existing '
            'LOCAL_PROVIDER_CONFIG_FILE"); '
            "managed = set(names); "
            "merged = {k: v for k, v in raw.items() if k not in managed}; "
            "merged.update(values); "
            "path.parent.mkdir(parents=True, exist_ok=True); "
            "path.write_text(json.dumps(merged, indent=2, "
            'sort_keys=True) + "\\n", encoding="utf-8")' "'" " && "
            'chmod 600 "$LOCAL_PROVIDER_CONFIG_FILE"'
        ),
    ],
    "external-publication-proof": [
        "mkdir -p .secrets && chmod 700 .secrets",
        (
            ': "${LINKEDIN_ACCESS_TOKEN:?set LINKEDIN_ACCESS_TOKEN first}" && '
            "umask 077 && printf '%s\\n' \"$LINKEDIN_ACCESS_TOKEN\" > "
            ".secrets/linkedin_access_token && "
            "chmod 600 .secrets/linkedin_access_token"
        ),
    ],
}

PROVIDER_PROOF_OPERATOR_SEQUENCE = [
    "configure credential_setup_requirements without printing secret values",
    "create or select durable product run UUID with product_run_bootstrap",
    "initialize proof workspace with workspace_commands",
    "validate proof workspace with workspace_validation_commands",
    "run preflight_checks and stop if any readiness gate fails",
    "execute proof commands and capture must_capture evidence",
    "generate, validate, and record the provider proof record",
    "rerun provider-proof-completion-status after both proofs are recorded",
    (
        "complete closure review, then record blocker-state update only "
        "after approved review"
    ),
]

PROVIDER_PROOF_PRODUCT_RUN_BOOTSTRAP_OUTPUT_FILE = (
    "social_media_optimiser/output/provider-proof/bootstrap/product-run.create.json"
)


def _product_run_bootstrap_request_body() -> str:
    payload = {
        "goal": "Agent Studio provider proof closeout",
        "input_mode": "text",
        "initial_context": {
            "proof_purpose": "provider_proof_closeout",
            "next_step": (
                "Use this run_id to initialize the provider proof workspace."
            ),
        },
    }
    return json.dumps(payload, separators=(",", ":"))


def _product_run_bootstrap_commands() -> list[str]:
    output_file = PROVIDER_PROOF_PRODUCT_RUN_BOOTSTRAP_OUTPUT_FILE
    return [
        "mkdir -p social_media_optimiser/output/provider-proof/bootstrap",
        (
            "curl -sS -X POST -o "
            f"{output_file} "
            "http://127.0.0.1:8000/api/runs "
            "-H 'Content-Type: application/json' "
            f"--data {shlex.quote(_product_run_bootstrap_request_body())}"
        ),
        (
            "uv run all-about-llms-admin "
            "init-provider-proof-workspace-from-bootstrap "
            f"--create-response-path {output_file} "
            "--output-root social_media_optimiser/output/provider-proof"
        ),
    ]


def _product_run_bootstrap_handoff() -> dict[str, object]:
    return {
        "api_path": "POST /api/runs",
        "output_file": PROVIDER_PROOF_PRODUCT_RUN_BOOTSTRAP_OUTPUT_FILE,
        "created_run_id_field": "run_id",
        "commands": _product_run_bootstrap_commands(),
        "next_step": (
            "rerun provider-proof-plan with the printed run_id and initialize "
            "social_media_optimiser/output/provider-proof/<run-id>"
        ),
    }


def _provider_proof_product_run_bootstrap_validation_payload(
    args: argparse.Namespace,
) -> dict[str, object]:
    checked_at = args.checked_at or date.today().isoformat()
    path = args.create_response_path
    safe_path = _provider_proof_workspace_report_path_text(path)
    issues: list[dict[str, str]] = []

    def add_issue(code: str, detail: str) -> None:
        issues.append({"code": code, "field": safe_path, "detail": detail})

    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(str(path)):
        add_issue(
            "bootstrap_path_secret_shape_detected",
            "create response path contains token-shaped text",
        )
    elif not path.exists():
        add_issue(
            "product_run_create_response_missing",
            "product-run.create.json was not found",
        )
    elif not path.is_file():
        add_issue(
            "product_run_create_response_not_file",
            "product-run.create.json path is not a file",
        )
    else:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            add_issue(
                "product_run_create_response_unreadable",
                "product-run.create.json could not be read",
            )
        except UnicodeDecodeError:
            add_issue(
                "product_run_create_response_not_utf8",
                "product-run.create.json must be UTF-8",
            )
        else:
            if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(content):
                add_issue(
                    "token_shaped_value_detected",
                    "product-run.create.json contains token-shaped text",
                )
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                add_issue(
                    "product_run_create_response_invalid_json",
                    "product-run.create.json must be valid JSON",
                )
            else:
                if not isinstance(parsed, Mapping):
                    add_issue(
                        "product_run_create_response_must_be_object",
                        "product-run.create.json must be a JSON object",
                    )
                elif not issues:
                    try:
                        run = RunState.model_validate(parsed)
                    except ValidationError:
                        add_issue(
                            "product_run_payload_schema_invalid",
                            (
                                "product-run.create.json must match "
                                "/api/runs response shape"
                            ),
                        )
                    else:
                        run_id = str(run.run_id)
                        output_dir = (
                            Path("social_media_optimiser/output/provider-proof")
                            / run_id
                        )
                        return {
                            "artifact": (
                                "agent-studio-provider-proof-product-run-"
                                "bootstrap-validation"
                            ),
                            "boundary": "no_secret_values_printed_no_state_change",
                            "checked_at": checked_at,
                            "status": "valid_product_run_bootstrap",
                            "create_response_path": safe_path,
                            "run_id": run_id,
                            "product_run_id_state": "product_run_uuid",
                            "issue_codes": [],
                            "issues": [],
                            "state_change_allowed": False,
                            "next_commands": [
                                (
                                    "uv run all-about-llms-admin "
                                    "init-provider-proof-workspace-from-bootstrap "
                                    f"--create-response-path {safe_path} "
                                    "--output-root "
                                    "social_media_optimiser/output/provider-proof"
                                ),
                                *_proof_plan_recheck_commands(run_id),
                                *_proof_workspace_commands(run_id),
                                *_proof_workspace_validation_commands_for_output(
                                    run_id,
                                    output_dir,
                                ),
                            ],
                        }

    return {
        "artifact": "agent-studio-provider-proof-product-run-bootstrap-validation",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": checked_at,
        "status": "invalid_product_run_bootstrap",
        "create_response_path": safe_path,
        "run_id": None,
        "product_run_id_state": "missing_or_invalid_product_run",
        "issue_codes": [issue["code"] for issue in issues],
        "issues": issues,
        "state_change_allowed": False,
        "next_commands": [],
    }


def _print_provider_proof_product_run_bootstrap_validation(
    args: argparse.Namespace,
) -> None:
    payload = _provider_proof_product_run_bootstrap_validation_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _provider_proof_workspace_from_bootstrap_payload(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    validation = _provider_proof_product_run_bootstrap_validation_payload(args)
    base_payload = {
        "artifact": "agent-studio-provider-proof-workspace-from-bootstrap",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": validation["checked_at"],
        "create_response_path": validation["create_response_path"],
        "create_response_validation_status": validation["status"],
        "state_change_allowed": False,
    }
    if validation["status"] != "valid_product_run_bootstrap":
        return {
            **base_payload,
            "status": validation["status"],
            "run_id": None,
            "product_run_id_state": validation["product_run_id_state"],
            "output_root": _provider_proof_workspace_report_path_text(
                args.output_root
            ),
            "output_dir": None,
            "issue_codes": validation["issue_codes"],
            "issues": validation["issues"],
            "written_files": [],
            "workspace_validation_commands": [],
        }

    run_id = str(validation["run_id"])
    output_dir = args.output_root / run_id
    workspace_payload = _provider_proof_workspace_payload(
        argparse.Namespace(
            env_example_path=args.env_example_path,
            checked_at=args.checked_at,
            run_id=run_id,
            output_dir=output_dir,
        ),
        env_values=env_values,
    )
    return {
        **base_payload,
        "status": workspace_payload["status"],
        "run_id": run_id,
        "product_run_id_state": validation["product_run_id_state"],
        "output_root": _provider_proof_workspace_report_path_text(args.output_root),
        "output_dir": workspace_payload["output_dir"],
        "issue_codes": workspace_payload.get("issue_codes", []),
        "issues": workspace_payload.get("issues", []),
        "written_files": workspace_payload.get("written_files", []),
        "workspace_validation_commands": workspace_payload.get(
            "validation_commands",
            [],
        ),
    }


def _print_provider_proof_workspace_from_bootstrap(args: argparse.Namespace) -> None:
    payload = _provider_proof_workspace_from_bootstrap_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))

PROVIDER_PROOF_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
PROVIDER_PROOF_SECRET_VALUE_PATTERN = re.compile(
    r"(hf_secret|livekit_(?:key|secret)|sk-[A-Za-z0-9]{20,}|"
    r"hf_[A-Za-z0-9]{20,}|livekit_[A-Za-z0-9]{20,})",
    re.IGNORECASE,
)
PROVIDER_PROOF_TEMPLATE_PLACEHOLDER_PATTERN = re.compile(r"^<[^>\n]+>$")
PROVIDER_PROOF_OPERATOR_SECRET_PATH_PATTERN = re.compile(
    r"(hf_secret|linkedin_secret|livekit_secret|sk-[A-Za-z0-9]{20,}|"
    r"hf_[A-Za-z0-9]{20,}|livekit_[A-Za-z0-9]{20,})",
    re.IGNORECASE,
)


def _provider_proof_normalized_publish_channel_platform(value: str) -> str:
    platform = value.strip().lower()
    return PUBLISH_CHANNEL_ALIASES.get(platform, platform)


def _provider_proof_publish_channels_are_canonical(channels: list[str]) -> bool:
    return (
        bool(channels)
        and all(channel in PUBLISH_CHANNEL_CREDENTIAL_ENVS for channel in channels)
        and len(channels) == len(set(channels))
    )


def _provider_proof_publish_channel_summary_entries(
    raw_channels: list[str],
) -> tuple[list[str], bool]:
    channels: list[str] = []
    entries_are_canonical = True
    for raw_channel in raw_channels:
        raw_platform = raw_channel.strip()
        platform = _provider_proof_normalized_publish_channel_platform(raw_channel)
        channels.append(platform)
        if raw_platform != platform:
            entries_are_canonical = False
    return channels, (
        entries_are_canonical
        and _provider_proof_publish_channels_are_canonical(channels)
    )


def _provider_proof_external_publication_channels_are_linkedin_only(
    channels: Sequence[str],
) -> bool:
    return list(channels) == ["linkedin"]


def _provider_proof_publish_channels_from_preflight(
    parsed: Mapping[str, object],
) -> list[str]:
    try:
        readiness = PublishReadinessResult.model_validate(parsed)
    except ValidationError:
        return []
    channels: list[str] = []
    for check in readiness.publish_channel_checks:
        platform = _provider_proof_normalized_publish_channel_platform(
            check.platform
        )
        if platform in PUBLISH_CHANNEL_CREDENTIAL_ENVS and platform not in channels:
            channels.append(platform)
    return channels


def _provider_proof_runtime_checks_from_preflight(
    parsed: Mapping[str, object],
) -> list[str]:
    try:
        readiness = VoiceRuntimeReadinessResult.model_validate(parsed)
    except ValidationError:
        return []
    ready_check_ids = {
        check.check_id
        for check in readiness.checks
        if _status_value(check.status) == "ready"
    }
    return [
        check_id
        for check_id in VOICE_PROOF_REQUIRED_RUNTIME_CHECKS
        if check_id in ready_check_ids
    ]


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _benchmark_speech_frame_limit(value: str) -> int:
    parsed = _positive_int(value)
    if parsed > MAX_RUST_VOICE_EDGE_BENCHMARK_SPEECH_FRAMES:
        raise argparse.ArgumentTypeError(
            "must be <= "
            f"{MAX_RUST_VOICE_EDGE_BENCHMARK_SPEECH_FRAMES} voice-edge frames"
        )
    return parsed


def _project_relative_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _env_example_items(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    items: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name = line.split("=", 1)[0].strip()
        value = line.split("=", 1)[1].strip()
        if name:
            items[name] = value
    return items


def _env_names_from_env_example(path: Path) -> set[str]:
    return set(_env_example_items(path))


def _provider_proof_operator_input_env_values(
    args: argparse.Namespace,
) -> dict[str, str | None]:
    input_path = getattr(args, "operator_input_path", None)
    if input_path is None:
        return {}
    try:
        parsed_inputs = _env_example_items(input_path)
    except (OSError, UnicodeError):
        return {}
    allowed_fields = {
        env_name
        for env_names in BLOCKER_CREDENTIAL_ENV_NAMES.values()
        for env_name in env_names
    } | {
        file_env_name
        for file_env_names in BLOCKER_SECRET_FILE_ENV_NAMES.values()
        for file_env_name in file_env_names.values()
    }
    operator_values: dict[str, str | None] = {}
    for field, raw_value in parsed_inputs.items():
        value = raw_value.strip()
        if (
            field in allowed_fields
            and value
            and not _provider_proof_record_template_placeholder(value)
        ):
            if field in PROVIDER_PROOF_OPERATOR_INPUT_URL_FIELDS:
                parsed_url = urlparse(value)
                allowed_url_schemes = (
                    {"ws", "wss"}
                    if field == "OPENROUTER_LIVEKIT_URL"
                    else {"http", "https"}
                )
                if parsed_url.scheme not in allowed_url_schemes or not parsed_url.netloc:
                    continue
                is_substitute_url = (
                    _provider_proof_openrouter_livekit_url_is_placeholder(value)
                    if field == "OPENROUTER_LIVEKIT_URL"
                    else _provider_proof_publication_destination_is_local_substitute(
                        value
                    )
                )
                if is_substitute_url:
                    continue
            if (
                field in PROVIDER_PROOF_OPERATOR_INPUT_SECRET_FILE_FIELDS
                and PROVIDER_PROOF_OPERATOR_SECRET_PATH_PATTERN.search(value)
            ):
                continue
            operator_values[field] = value
    return operator_values


def _blocker_credential_snapshot_payload(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    blocker_env_names = {
        env_name
        for env_names in BLOCKER_CREDENTIAL_ENV_NAMES.values()
        for env_name in env_names
    }
    secret_file_env_names = {
        file_env_name
        for file_env_names in BLOCKER_SECRET_FILE_ENV_NAMES.values()
        for file_env_name in file_env_names.values()
    }
    checked_at = args.checked_at or date.today().isoformat()
    actual_env_values = env_values
    if actual_env_values is None:
        actual_env_values = {
            env_name: os.environ.get(env_name)
            for env_name in sorted(
                blocker_env_names
                | secret_file_env_names
                | {"LIVEKIT_URL", "LOCAL_PROVIDER_CONFIG_FILE"}
            )
        }
    operator_input_env_values = _provider_proof_operator_input_env_values(args)
    if actual_env_values is env_values:
        actual_env_values = dict(actual_env_values)
    actual_env_values.update(operator_input_env_values)

    env_example_items = _env_example_items(args.env_example_path)
    placeholder_env_names = set(env_example_items)
    configured_file_env_names = _configured_secret_file_env_names(
        file_env_names=secret_file_env_names,
        env_values=actual_env_values,
        env_example_items=env_example_items,
        base_path=args.env_example_path.parent,
    )
    configured_local_provider_env_names = _configured_local_provider_env_names(
        env_values=actual_env_values,
        env_example_items=env_example_items,
        base_path=args.env_example_path.parent,
    )
    snapshots = build_blocker_credential_snapshots(
        env_values=actual_env_values,
        placeholder_env_names=placeholder_env_names,
        configured_file_env_names=configured_file_env_names,
        configured_local_provider_env_names=configured_local_provider_env_names,
        checked_at=checked_at,
    )
    return {
        "artifact": "agent-studio-blocker-credential-snapshots",
        "source": _provider_proof_portable_path_text(args.env_example_path),
        "checked_at": checked_at,
        "boundary": "no_secret_values_printed",
        "snapshots": snapshots,
    }


def _configured_secret_file_env_names(
    *,
    file_env_names: set[str],
    env_values: Mapping[str, str | None],
    env_example_items: Mapping[str, str],
    base_path: Path,
) -> set[str]:
    configured: set[str] = set()
    for file_env_name in file_env_names:
        raw_path = env_values.get(file_env_name) or env_example_items.get(
            file_env_name
        )
        if not raw_path:
            continue
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = base_path / path
        try:
            if not path.is_file() or path.stat().st_size <= 0:
                continue
            value = path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            continue
        if not value or PROVIDER_PROOF_TEMPLATE_PLACEHOLDER_PATTERN.fullmatch(value):
            continue
        configured.add(file_env_name)
    return configured


def _configured_local_provider_env_names(
    *,
    env_values: Mapping[str, str | None],
    env_example_items: Mapping[str, str],
    base_path: Path,
) -> set[str]:
    raw_path = env_values.get("LOCAL_PROVIDER_CONFIG_FILE") or env_example_items.get(
        "LOCAL_PROVIDER_CONFIG_FILE"
    )
    if not raw_path:
        return set()
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = base_path / path
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return set()
    if not isinstance(parsed, dict):
        return set()

    configured: set[str] = set()
    for env_name in LocalProviderConfigEnvName:
        raw_value = parsed.get(str(env_name))
        if not isinstance(raw_value, str):
            continue
        try:
            validate_local_provider_config_value(env_name, raw_value)
        except ValueError:
            continue
        configured.add(str(env_name))
    return configured


def _print_blocker_credential_snapshots(args: argparse.Namespace) -> None:
    payload = _blocker_credential_snapshot_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _proof_plan_run_id_state(run_id: str) -> str:
    value = run_id.strip()
    if not value or value == "<run-id>":
        return "placeholder_run_id"
    if (
        not PROVIDER_PROOF_RUN_ID_PATTERN.fullmatch(value)
        or PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(value)
    ):
        return "unsafe_run_id"
    return "concrete_run_id"


def _proof_plan_product_run_id_state(
    run_id: str,
    *,
    run_id_state: str,
) -> str:
    if run_id_state != "concrete_run_id":
        return run_id_state
    try:
        UUID(run_id.strip())
    except ValueError:
        return "non_uuid_run_id"
    return "product_run_uuid"


def _proof_plan_status(
    snapshot: Mapping[str, object],
    *,
    run_id_state: str,
    product_run_id_state: str,
) -> str:
    if run_id_state in {"placeholder_run_id", "unsafe_run_id"}:
        return "blocked_by_run_id"
    if snapshot.get("state") != "runtime_configuration_present_unverified":
        return "blocked_by_credentials"
    if product_run_id_state != "product_run_uuid":
        return "blocked_by_run_id"
    return "ready_for_runtime_attempt"


def _proof_plan_blocking_reasons(
    snapshot: Mapping[str, object],
    *,
    run_id_state: str,
    product_run_id_state: str,
) -> list[str]:
    reasons: list[str] = []
    if run_id_state == "placeholder_run_id":
        reasons.append("run_id_not_concrete")
    elif run_id_state == "unsafe_run_id":
        reasons.append("run_id_unsafe")

    credential_state = snapshot.get("state")
    if credential_state != "runtime_configuration_present_unverified":
        reasons.append(str(credential_state))
    elif product_run_id_state == "non_uuid_run_id":
        reasons.append("run_id_not_product_uuid")
    return reasons


def _proof_plan_unblock_when(
    requirements: list[str],
    *,
    run_id_state: str,
    product_run_id_state: str,
) -> list[str]:
    if run_id_state == "placeholder_run_id":
        return [*requirements, "durable product run UUID replaces <run-id>"]
    if run_id_state == "unsafe_run_id":
        return [*requirements, "run id contains unsupported characters"]
    if product_run_id_state == "non_uuid_run_id":
        return [*requirements, "durable product run UUID replaces run id"]
    return requirements


def _run_id_required_before_execution() -> bool:
    return True


def _proof_plan_command_run_id(run_id: str, *, run_id_state: str) -> str:
    if run_id_state == "concrete_run_id":
        return run_id.strip()
    return "<run-id>"


def _proof_product_run_id_command_value(
    run_id: str,
    *,
    product_run_id_state: str,
) -> str:
    if product_run_id_state == "product_run_uuid":
        return run_id.strip()
    return "<run-id>"


PROVIDER_PROOF_COMMAND_PLACEHOLDERS = {
    "<preflight-validation.json>",
    "<workspace-validation.json>",
}


def _proof_command_arg(value: object) -> str:
    text = str(value)
    if text in PROVIDER_PROOF_COMMAND_PLACEHOLDERS:
        return text
    return shlex.quote(_provider_proof_output_path_text(text))


def _proof_record_commands(
    proof_name: str,
    run_id: str,
    *,
    preflight_validation_path: object = "<preflight-validation.json>",
    workspace_validation_path: object = "<workspace-validation.json>",
) -> list[str]:
    preflight_validation_arg = _proof_command_arg(preflight_validation_path)
    workspace_validation_arg = _proof_command_arg(workspace_validation_path)
    return [
        (
            "uv run all-about-llms-admin record-provider-proof-record "
            f"--proof {proof_name} --run-id {run_id} "
            "--record-path <provider-proof-record.json> "
            f"--preflight-validation-path {preflight_validation_arg} "
            f"--workspace-validation-path {workspace_validation_arg}"
        )
    ]


def _proof_record_template_commands(proof_name: str, run_id: str) -> list[str]:
    return [
        (
            "uv run all-about-llms-admin provider-proof-record-template "
            f"--proof {proof_name} --run-id {run_id}"
        )
    ]


def _proof_completion_status_commands(
    run_id: str,
    *,
    output_dir: Path | None = None,
) -> list[str]:
    command = (
        "uv run all-about-llms-admin provider-proof-completion-status "
        f"--run-id {run_id}"
    )
    if output_dir is not None:
        output_dir_text = _provider_proof_command_path_text(output_dir)
        command = f"{command} --output-dir {_proof_command_arg(output_dir_text)}"
    return [command]


def _proof_completion_status_command_with_output_dir(
    command: str,
    output_dir: Path,
) -> str:
    if " provider-proof-completion-status " not in command:
        return command
    if " --output-dir " in command:
        return command
    redirect_marker = " > "
    if redirect_marker in command:
        before_redirect, after_redirect = command.split(redirect_marker, 1)
        output_dir_text = _provider_proof_command_path_text(output_dir)
        return (
            f"{before_redirect} --output-dir {_proof_command_arg(output_dir_text)}"
            f"{redirect_marker}{after_redirect}"
        )
    output_dir_text = _provider_proof_command_path_text(output_dir)
    return f"{command} --output-dir {_proof_command_arg(output_dir_text)}"


def _proof_plan_recheck_commands(run_id: str) -> list[str]:
    return [
        (
            "uv run all-about-llms-admin provider-proof-plan "
            f"--run-id {run_id}"
        )
    ]


def _proof_workspace_commands(run_id: str) -> list[str]:
    return [
        (
            "uv run all-about-llms-admin init-provider-proof-workspace "
            f"--run-id {run_id} --output-dir "
            f"social_media_optimiser/output/provider-proof/{run_id}"
        )
    ]


def _proof_workspace_commands_for_output(run_id: str, output_dir: Path) -> list[str]:
    return [
        (
            "uv run all-about-llms-admin init-provider-proof-workspace "
            f"--run-id {run_id} --output-dir {_proof_command_arg(output_dir)}"
        )
    ]


def _proof_workspace_validation_commands_for_output(
    run_id: str,
    output_dir: Path,
) -> list[str]:
    return [
        (
            "uv run all-about-llms-admin validate-provider-proof-workspace "
            f"--run-id {run_id} --output-dir {_proof_command_arg(output_dir)}"
        )
    ]


def _proof_workspace_validation_report_files(run_id: str) -> list[str]:
    base = f"social_media_optimiser/output/provider-proof/{run_id}"
    return [f"{base}/workspace-validation.json"]


def _proof_workspace_validation_report_files_for_output(output_dir: Path) -> list[str]:
    return [str(output_dir / "workspace-validation.json")]


def _proof_workspace_validation_capture_commands_for_output(
    run_id: str,
    output_dir: Path,
) -> list[str]:
    report_path = _proof_workspace_validation_report_files_for_output(output_dir)[0]
    return [
        (
            f"{_proof_workspace_validation_commands_for_output(run_id, output_dir)[0]} "
            f"> {_proof_command_arg(report_path)}"
        )
    ]


def _proof_workspace_expected_files(run_id: str) -> list[str]:
    base = f"social_media_optimiser/output/provider-proof/{run_id}"
    return [
        f"{base}/provider-backed-live-voice-proof.template.json",
        f"{base}/external-publication-proof.template.json",
        f"{base}/operator-inputs.template.env",
        f"{base}/README.md",
    ]


def _proof_preflight_output_files(proof_name: str, run_id: str) -> list[str]:
    return _proof_preflight_output_files_for_output(
        proof_name,
        Path(f"social_media_optimiser/output/provider-proof/{run_id}"),
    )


def _proof_preflight_output_files_for_output(
    proof_name: str,
    output_dir: Path,
) -> list[str]:
    base = str(output_dir)
    product_run_file = f"{base}/product-run.preflight.json"
    if proof_name == "provider-backed-live-voice-proof":
        return [
            product_run_file,
            f"{base}/provider-readiness.preflight.json",
            f"{base}/voice-runtime-readiness.preflight.json",
        ]
    return [product_run_file, f"{base}/publish-readiness.preflight.json"]


def _proof_preflight_capture_commands(proof_name: str, run_id: str) -> list[str]:
    return _proof_preflight_capture_commands_for_output(
        proof_name,
        run_id,
        Path(f"social_media_optimiser/output/provider-proof/{run_id}"),
    )


def _proof_preflight_capture_commands_for_output(
    proof_name: str,
    run_id: str,
    output_dir: Path,
    *,
    acknowledge_publish_channel_policy: bool = False,
) -> list[str]:
    output_files = _proof_preflight_output_files_for_output(proof_name, output_dir)
    product_run_url = f"http://127.0.0.1:8000/api/runs/{run_id}"
    product_run_command = (
        "curl -sS -o "
        f"{_proof_command_arg(output_files[0])} "
        f"{shlex.quote(product_run_url)}"
    )
    if proof_name == "provider-backed-live-voice-proof":
        provider_readiness_url = "http://127.0.0.1:8000/api/provider-readiness"
        voice_readiness_url = (
            "http://127.0.0.1:8000/api/voice-runtime-readiness?"
            "preflight_gemma=true&preflight_tts=true&"
            "preflight_livekit=true&preflight_edge=true&preflight_agent=true"
        )
        return [
            product_run_command,
            (
                "curl -sS -o "
                f"{_proof_command_arg(output_files[1])} "
                f"{shlex.quote(provider_readiness_url)}"
            ),
            (
                "curl -sS -o "
                f"{_proof_command_arg(output_files[2])} "
                f"{shlex.quote(voice_readiness_url)}"
            ),
        ]

    publish_readiness_url = (
        f"http://127.0.0.1:8000/api/runs/{run_id}/publish-readiness"
    )
    request_body = _publication_proof_preflight_request_body(
        acknowledge_publish_channel_policy=acknowledge_publish_channel_policy,
    )
    return [
        product_run_command,
        (
            "curl -sS -X POST -o "
            f"{_proof_command_arg(output_files[1])} "
            f"{shlex.quote(publish_readiness_url)} "
            "-H 'Content-Type: application/json' "
            f"--data {shlex.quote(request_body)}"
        )
    ]


def _proof_preflight_artifact_id_fields(proof_name: str) -> list[str]:
    if proof_name == "provider-backed-live-voice-proof":
        return [
            "product_run_preflight_artifact_id",
            "provider_readiness_preflight_artifact_id",
            "voice_runtime_readiness_preflight_artifact_id",
        ]
    return [
        "product_run_preflight_artifact_id",
        "publish_readiness_preflight_artifact_id",
    ]


def _proof_preflight_artifact_ids_for_output(
    proof_name: str,
    output_dir: Path,
) -> dict[str, str]:
    fields = _proof_preflight_artifact_id_fields(proof_name)
    output_files = _proof_preflight_output_files_for_output(proof_name, output_dir)
    return dict(zip(fields, output_files, strict=True))


def _proof_preflight_validation_commands(
    proof_name: str,
    run_id: str,
) -> list[str]:
    return _proof_preflight_validation_commands_for_output(
        proof_name,
        run_id,
        Path(f"social_media_optimiser/output/provider-proof/{run_id}"),
    )


def _proof_preflight_validation_commands_for_output(
    proof_name: str,
    run_id: str,
    output_dir: Path,
) -> list[str]:
    return [
        (
            "uv run all-about-llms-admin "
            "validate-provider-proof-preflight-artifacts "
            f"--proof {proof_name} --run-id {run_id} "
            f"--preflight-dir {_proof_command_arg(output_dir)}"
        )
    ]


def _proof_preflight_validation_report_files(
    proof_name: str,
    run_id: str,
) -> list[str]:
    return _proof_preflight_validation_report_files_for_output(
        proof_name,
        Path(f"social_media_optimiser/output/provider-proof/{run_id}"),
    )


def _proof_preflight_validation_report_files_for_output(
    proof_name: str,
    output_dir: Path,
) -> list[str]:
    return [str(output_dir / f"{proof_name}.preflight-validation.json")]


def _proof_preflight_validation_capture_commands(
    proof_name: str,
    run_id: str,
) -> list[str]:
    return _proof_preflight_validation_capture_commands_for_output(
        proof_name,
        run_id,
        Path(f"social_media_optimiser/output/provider-proof/{run_id}"),
    )


def _proof_preflight_validation_capture_commands_for_output(
    proof_name: str,
    run_id: str,
    output_dir: Path,
) -> list[str]:
    validation_command = _proof_preflight_validation_commands_for_output(
        proof_name,
        run_id,
        output_dir,
    )[0]
    report_file = _proof_preflight_validation_report_files_for_output(
        proof_name,
        output_dir,
    )[0]
    return [f"{validation_command} > {_proof_command_arg(report_file)}"]


def _proof_preflight_validation_requirements(proof_name: str) -> list[str]:
    if proof_name == "provider-backed-live-voice-proof":
        return [
            *_product_run_preflight_validation_requirements(),
            (
                "provider-readiness.preflight.json must select ready "
                "openrouter-livekit"
            ),
            (
                "voice-runtime-readiness.preflight.json must be ready for "
                "openrouter_livekit"
            ),
            (
                "voice runtime preflight flags must include livekit, edge, "
                "agent, OpenRouter reasoning, and tts"
            ),
            (
                "required runtime checks must be present once and ready: "
                + ", ".join(VOICE_PROOF_REQUIRED_RUNTIME_CHECKS)
            ),
        ]
    if proof_name == "external-publication-proof":
        return [
            *_product_run_preflight_validation_requirements(),
            (
                "publish-readiness.preflight.json status must be ready with "
                "ready=true and no top-level or channel blocking issues, or "
                "needs_review with ready=false and only "
                "publish_channel_policy_review_required"
            ),
            (
                "publish-readiness.preflight.json must include one "
                "normalized, non-empty supported publish_channel_checks entry "
                "per channel"
            ),
            "publish channel credentials must be configured",
            (
                "publish channel policy status must be acknowledged when "
                "status is ready; policy-review handoff must include at "
                "least one needs_review channel policy, channel blockers must "
                "be empty or policy-review-only, and acknowledged channels "
                "must not carry policy-review blockers"
            ),
            "publish readiness must not open a feedback gate",
        ]
    raise ValueError(f"unknown proof name: {proof_name}")


PROVIDER_PROOF_COMMANDS_ALLOWED_AFTER = [
    "proof workspace initialized",
    "proof workspace validation status is valid_workspace",
    "preflight output files captured",
    "preflight validation report status is valid_preflight_artifacts",
    "proof-specific human confirmations are complete",
]


def _proof_attempt_gate(
    proof_name: str,
    *,
    status: str,
    blocking_reasons: list[str],
    command_run_id: str,
) -> dict[str, object]:
    if status == "ready_for_runtime_attempt":
        return {
            "state": "ready_for_preflight_capture",
            "can_run_preflight_capture": True,
            "can_run_proof_commands": False,
            "blocked_by": [],
            "next_action": "initialize_workspace_and_capture_preflight",
            "next_action_commands": [
                *_proof_workspace_commands(command_run_id),
                *_proof_workspace_validation_commands_for_output(
                    command_run_id,
                    Path(f"social_media_optimiser/output/provider-proof/{command_run_id}"),
                ),
                *_proof_preflight_capture_commands(proof_name, command_run_id),
                *_proof_preflight_validation_capture_commands(
                    proof_name,
                    command_run_id,
                ),
            ],
            "proof_commands_allowed_after": (
                PROVIDER_PROOF_COMMANDS_ALLOWED_AFTER
            ),
            "state_change_allowed": False,
    }
    if status == "blocked_by_run_id":
        next_action = "replace_run_id"
        next_action_commands = _product_run_bootstrap_commands()
    else:
        next_action = "configure_credentials"
        next_action_commands = [
            *PROVIDER_PROOF_CREDENTIAL_SETUP_COMMANDS[proof_name],
            *_proof_plan_recheck_commands(command_run_id),
        ]
    return {
        "state": status,
        "can_run_preflight_capture": False,
        "can_run_proof_commands": False,
        "blocked_by": blocking_reasons,
        "next_action": next_action,
        "next_action_commands": next_action_commands,
        "proof_commands_allowed_after": PROVIDER_PROOF_COMMANDS_ALLOWED_AFTER,
        "state_change_allowed": False,
    }


def _proof_closure_review_template_commands(
    run_id: str,
    audit_targets: list[str] | None = None,
) -> list[str]:
    command = (
        "uv run all-about-llms-admin "
        f"provider-proof-closure-review-template --run-id {run_id}"
    )
    for target in audit_targets or []:
        command = (
            f"{command} --audit-target "
            f"{shlex.quote(_provider_proof_output_path_text(target))}"
        )
    return [command]


def _proof_closure_review_validation_commands(
    run_id: str,
    audit_targets: list[str] | None = None,
) -> list[str]:
    command = (
        "uv run all-about-llms-admin "
        "validate-provider-proof-closure-review "
        f"--run-id {run_id} "
        "--record-path <provider-proof-closure-review.json>"
    )
    for target in audit_targets or []:
        command = (
            f"{command} --audit-target "
            f"{shlex.quote(_provider_proof_output_path_text(target))}"
        )
    return [command]


def _proof_closure_review_record_commands(
    run_id: str,
    proof_audit_targets: list[str] | None = None,
) -> list[str]:
    command = (
        "uv run all-about-llms-admin "
        "record-provider-proof-closure-review "
        f"--run-id {run_id} "
        "--record-path <provider-proof-closure-review.json>"
    )
    for target in proof_audit_targets or []:
        command = (
            f"{command} --proof-audit-target "
            f"{shlex.quote(_provider_proof_output_path_text(target))}"
        )
    return [command]


def _proof_closure_review_status_commands(
    run_id: str,
    proof_audit_targets: list[str] | None = None,
    review_audit_targets: list[str] | None = None,
) -> list[str]:
    command = (
        "uv run all-about-llms-admin "
        f"provider-proof-closure-review-status --run-id {run_id}"
    )
    for target in proof_audit_targets or []:
        command = (
            f"{command} --proof-audit-target "
            f"{shlex.quote(_provider_proof_output_path_text(target))}"
        )
    for target in review_audit_targets or []:
        command = (
            f"{command} --audit-target "
            f"{shlex.quote(_provider_proof_output_path_text(target))}"
        )
    return [command]


def _proof_blocker_state_update_record_commands(
    run_id: str,
    proof_audit_targets: list[str] | None = None,
    closure_review_audit_targets: list[str] | None = None,
    blocker_update_audit_targets: list[str] | None = None,
) -> list[str]:
    command = (
        "uv run all-about-llms-admin "
        f"record-provider-proof-blocker-state-update --run-id {run_id}"
    )
    for target in proof_audit_targets or []:
        command = (
            f"{command} --proof-audit-target "
            f"{shlex.quote(_provider_proof_output_path_text(target))}"
        )
    for target in closure_review_audit_targets or []:
        command = (
            f"{command} --closure-review-audit-target "
            f"{shlex.quote(_provider_proof_output_path_text(target))}"
        )
    for target in blocker_update_audit_targets or []:
        command = (
            f"{command} --audit-target "
            f"{shlex.quote(_provider_proof_output_path_text(target))}"
        )
    return [command]


def _proof_closeout_commands(run_id: str) -> list[str]:
    return [
        *_proof_completion_status_commands(run_id),
        *_proof_closure_review_template_commands(run_id),
        *_proof_closure_review_validation_commands(run_id),
        *_proof_closure_review_record_commands(run_id),
        *_proof_closure_review_status_commands(run_id),
        *_proof_blocker_state_update_record_commands(run_id),
    ]


def _proof_current_blocker_matrix_command(run_id: str, output_dir: Path) -> str:
    output_dir_text = _provider_proof_command_path_text(output_dir)
    return (
        "uv run all-about-llms-admin provider-proof-current-blocker-matrix "
        f"--run-id {run_id} --output-dir {_proof_command_arg(output_dir_text)}"
    )


def _proof_current_blocker_matrix_capture_command(
    run_id: str,
    output_dir: Path,
) -> str:
    report_path = _provider_proof_command_path_text(
        output_dir / "current-blocker-matrix.json"
    )
    return (
        f"{_proof_current_blocker_matrix_command(run_id, output_dir)} > "
        f"{_proof_command_arg(report_path)}"
    )


def _proof_operator_unblocker_checklist_command(
    run_id: str,
    output_dir: Path,
) -> str:
    output_dir_text = _provider_proof_command_path_text(output_dir)
    return (
        "uv run all-about-llms-admin provider-proof-operator-unblocker-checklist "
        f"--run-id {run_id} --output-dir {_proof_command_arg(output_dir_text)}"
    )


def _proof_operator_unblocker_checklist_capture_command(
    run_id: str,
    output_dir: Path,
) -> str:
    return (
        f"{_proof_operator_unblocker_checklist_command(run_id, output_dir)} > "
        f"{_proof_command_arg(_provider_proof_command_path_text(output_dir / 'operator-unblocker-checklist.md'))}"
    )


def _proof_current_status_command(run_id: str, output_dir: Path) -> str:
    output_dir_text = _provider_proof_command_path_text(output_dir)
    return (
        "uv run all-about-llms-admin provider-proof-current-status "
        f"--run-id {run_id} --output-dir {_proof_command_arg(output_dir_text)}"
    )


def _proof_current_status_capture_command(run_id: str, output_dir: Path) -> str:
    report_path = _provider_proof_command_path_text(
        output_dir / "current-proof-status.md"
    )
    return (
        f"{_proof_current_status_command(run_id, output_dir)} > "
        f"{_proof_command_arg(report_path)}"
    )


def _proof_operator_input_readiness_command(
    run_id: str,
    output_dir: Path,
    *,
    fail_on_blocked: bool = False,
) -> str:
    input_path = _provider_proof_command_path_text(
        output_dir / "operator-inputs.template.env"
    )
    command = (
        "uv run all-about-llms-admin provider-proof-operator-input-readiness "
        f"--run-id {run_id} --input-path {_proof_command_arg(input_path)}"
    )
    if fail_on_blocked:
        command = f"{command} --fail-on-blocked"
    return command


def _proof_operator_input_readiness_capture_command(
    run_id: str,
    output_dir: Path,
    *,
    fail_on_blocked: bool = False,
) -> str:
    report_path = _provider_proof_command_path_text(
        output_dir / "operator-input-readiness.json"
    )
    readiness_command = _proof_operator_input_readiness_command(
        run_id,
        output_dir,
        fail_on_blocked=fail_on_blocked,
    )
    return (
        f"{readiness_command} > "
        f"{_proof_command_arg(report_path)}"
    )


def _proof_operator_input_readiness_capture_command_for_input(
    run_id: str,
    input_path: Path,
    *,
    fail_on_blocked: bool = False,
) -> str:
    report_path = _provider_proof_command_path_text(
        input_path.parent / "operator-input-readiness.json"
    )
    input_path_text = _provider_proof_command_path_text(input_path)
    command = (
        "uv run all-about-llms-admin provider-proof-operator-input-readiness "
        f"--run-id {run_id} --input-path {_proof_command_arg(input_path_text)}"
    )
    if fail_on_blocked:
        command = f"{command} --fail-on-blocked"
    return f"{command} > {_proof_command_arg(report_path)}"


def _proof_operator_input_retry_commands_for_input(
    run_id: str,
    input_path: Path,
    *,
    fail_on_blocked: bool = False,
) -> list[str]:
    output_dir = input_path.parent
    input_path_arg = _proof_command_arg(_provider_proof_command_path_text(input_path))
    credential_snapshot_path = _proof_command_arg(
        _provider_proof_command_path_text(output_dir / "credential-snapshot.json")
    )
    proof_plan_path = _proof_command_arg(
        _provider_proof_command_path_text(output_dir / "proof-plan.json")
    )
    return [
        _proof_operator_input_readiness_capture_command_for_input(
            run_id,
            input_path,
            fail_on_blocked=fail_on_blocked,
        ),
        (
            "uv run all-about-llms-admin blocker-credential-snapshot "
            f"--operator-input-path {input_path_arg} > {credential_snapshot_path}"
        ),
        (
            "uv run all-about-llms-admin provider-proof-plan "
            f"--run-id {run_id} --operator-input-path {input_path_arg} > "
            f"{proof_plan_path}"
        ),
        _proof_current_blocker_matrix_capture_command(run_id, output_dir),
        _proof_current_status_capture_command(run_id, output_dir),
        _proof_operator_unblocker_checklist_capture_command(run_id, output_dir),
    ]


def _provider_proof_operator_input_command_path(
    operator_input_readiness: Mapping[str, object],
    output_dir: Path,
) -> Path:
    raw_input_path = operator_input_readiness.get("input_path")
    if isinstance(raw_input_path, str) and raw_input_path.strip():
        input_path_text = raw_input_path.strip()
        if not PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(input_path_text):
            workspace_prefix = "<workspace-root>/"
            if input_path_text.startswith(workspace_prefix):
                return PROJECT_ROOT / input_path_text.removeprefix(workspace_prefix)
            if input_path_text == "<workspace-root>":
                return PROJECT_ROOT
            return Path(input_path_text)
    return output_dir / "operator-inputs.template.env"


def _provider_proof_operator_input_blocks_proof(
    proof_name: str,
    operator_input_readiness: Mapping[str, object],
) -> bool:
    blocked_statuses = {
        "blocked_by_operator_inputs",
        "invalid_operator_input_file",
    }
    proofs = operator_input_readiness.get("proofs")
    if isinstance(proofs, Mapping):
        proof_payload = proofs.get(proof_name)
        if isinstance(proof_payload, Mapping):
            proof_state = proof_payload.get("state") or proof_payload.get("status")
            if str(proof_state) in blocked_statuses:
                return True
            blocked_fields = proof_payload.get("blocked_fields", [])
            if isinstance(blocked_fields, list):
                return any(str(field).strip() for field in blocked_fields)
            return False

    global_status = str(operator_input_readiness.get("status", ""))
    if global_status == "invalid_operator_input_file":
        return True
    if global_status != "blocked_by_operator_inputs":
        return False
    required_fields = {
        str(field)
        for field in PROVIDER_PROOF_OPERATOR_INPUT_FIELDS.get(proof_name, [])
    }
    blocked_fields = operator_input_readiness.get("blocked_fields", [])
    if not isinstance(blocked_fields, list):
        return False
    return any(str(field) in required_fields for field in blocked_fields)


def _provider_proof_operator_input_gate_commands_for_proof(
    proof_name: str,
    run_id: str,
    output_dir: Path,
    operator_input_readiness: Mapping[str, object] | None = None,
) -> list[str]:
    readiness = operator_input_readiness
    if readiness is None:
        readiness = _provider_proof_json_object(
            output_dir / "operator-input-readiness.json"
        )
    if not readiness or not _provider_proof_operator_input_blocks_proof(
        proof_name,
        readiness,
    ):
        return []

    guarded_commands = readiness.get("guarded_next_action_commands")
    if isinstance(guarded_commands, list):
        commands = [
            str(command)
            for command in guarded_commands
            if isinstance(command, str) and command
        ]
        if commands:
            return commands

    input_path = _provider_proof_operator_input_command_path(readiness, output_dir)
    return _proof_operator_input_retry_commands_for_input(
        run_id,
        input_path,
        fail_on_blocked=True,
    )


def _runtime_health_ledger_commands(run_id: str) -> list[str]:
    return [
        (
            "uv run all-about-llms-admin build-runtime-health-ledger "
            f"--run-id {run_id}"
        )
    ]


def _voice_agent_process_start_command(*, output_path: Path | None = None) -> str:
    output_arg = f"-o {_proof_command_arg(output_path)} " if output_path else ""
    return (
        f"curl -sS -X POST {output_arg}"
        "http://127.0.0.1:8000/api/voice-agent-process/start "
        "-H 'Content-Type: application/json' "
        "--data '{\"dev\":true,\"unregistered\":false,\"force_restart\":false}'"
    )


def _proof_execution_capture_commands_for_output(
    proof_name: str,
    run_id: str,
    output_dir: Path,
) -> list[str]:
    if proof_name == "provider-backed-live-voice-proof":
        return [
            _voice_agent_process_start_command(
                output_path=output_dir / "voice-agent-process.start.json"
            ),
            *_live_voice_evidence_commands(run_id, output_dir=output_dir),
        ]
    if proof_name == "external-publication-proof":
        return [
            (
                "uv run all-about-llms-admin "
                f"build-distribution-package --run-id {run_id} "
                f"> {_proof_command_arg(output_dir / 'distribution-package.json')}"
            )
        ]
    return _proof_execution_commands(proof_name, run_id)


def _livekit_voice_timing_capture_command(
    run_id: str,
    *,
    output_path: Path | None = None,
) -> str:
    command = (
        "uv run all-about-llms-admin "
        f"capture-livekit-voice-timing-proof --run-id {run_id}"
    )
    if output_path is None:
        return command
    return f"{command} > {_proof_command_arg(output_path)}"


def _live_voice_evidence_commands(
    run_id: str,
    *,
    output_dir: Path | None = None,
) -> list[str]:
    capture_output_path = (
        output_dir / "livekit-voice-timing-capture.json"
        if output_dir is not None
        else None
    )
    return [
        *_runtime_health_ledger_commands(run_id),
        (
            "uv run all-about-llms-admin "
            "build-provider-smoke-ledger "
            f"--run-id {run_id} --live "
            "--realtime-provider openrouter_livekit "
            "--skip-gemma --skip-web-search"
        ),
        _livekit_voice_timing_capture_command(
            run_id,
            output_path=capture_output_path,
        ),
        (
            "uv run all-about-llms-admin "
            "build-realtime-voice-timing-ledger "
            f"--run-id {run_id}"
        ),
    ]


def _proof_execution_commands(proof_name: str, run_id: str) -> list[str]:
    if proof_name == "provider-backed-live-voice-proof":
        return [
            _voice_agent_process_start_command(),
            *_live_voice_evidence_commands(run_id),
        ]
    if proof_name == "external-publication-proof":
        return [
            (
                "uv run all-about-llms-admin "
                f"build-distribution-package --run-id {run_id}"
            )
        ]
    return []


def _proof_record_next_commands(
    proof_name: str,
    run_id: str,
    *,
    preflight_validation_path: object = "<preflight-validation.json>",
    workspace_validation_path: object = "<workspace-validation.json>",
) -> list[str]:
    preflight_validation_arg = _proof_command_arg(preflight_validation_path)
    workspace_validation_arg = _proof_command_arg(workspace_validation_path)
    return [
        (
            "uv run all-about-llms-admin validate-provider-proof-record "
            f"--proof {proof_name} --run-id {run_id} "
            "--record-path <provider-proof-record.json> "
            f"--preflight-validation-path {preflight_validation_arg} "
            f"--workspace-validation-path {workspace_validation_arg}"
        ),
        *_proof_record_commands(
            proof_name,
            run_id,
            preflight_validation_path=preflight_validation_path,
            workspace_validation_path=workspace_validation_path,
        ),
    ]


def _product_run_preflight_checks(run_id: str) -> list[str]:
    return [f"GET /api/runs/{run_id}"]


def _product_run_preflight_commands(run_id: str) -> list[str]:
    product_run_url = f"http://127.0.0.1:8000/api/runs/{run_id}"
    return [f"curl -sS {shlex.quote(product_run_url)}"]


def _product_run_preflight_validation_requirements() -> list[str]:
    return [
        (
            "product-run.preflight.json must match /api/runs/<run-id> response "
            "shape and run_id must match command_run_id"
        )
    ]


def _voice_proof_preflight_checks(run_id: str) -> list[str]:
    return [
        *_product_run_preflight_checks(run_id),
        "GET /api/provider-readiness",
        (
            "GET /api/voice-runtime-readiness?"
            "preflight_gemma=true&preflight_tts=true&"
            "preflight_livekit=true&preflight_edge=true&preflight_agent=true"
        ),
        "confirm selected realtime provider is openrouter_livekit before live smoke",
    ]


def _voice_proof_preflight_commands(run_id: str) -> list[str]:
    provider_readiness_url = "http://127.0.0.1:8000/api/provider-readiness"
    voice_readiness_url = (
        "http://127.0.0.1:8000/api/voice-runtime-readiness?"
        "preflight_gemma=true&preflight_tts=true&"
        "preflight_livekit=true&preflight_edge=true&preflight_agent=true"
    )
    return [
        *_product_run_preflight_commands(run_id),
        f"curl -sS {shlex.quote(provider_readiness_url)}",
        f"curl -sS {shlex.quote(voice_readiness_url)}",
    ]


def _publication_proof_preflight_checks(run_id: str) -> list[str]:
    return [
        *_product_run_preflight_checks(run_id),
        f"POST /api/runs/{run_id}/publish-readiness",
        "confirm human approval and channel policy acknowledgement",
        "confirm disclosure-bearing artifact snapshot before destination proof",
    ]


def _publication_proof_preflight_commands(run_id: str) -> list[str]:
    publish_readiness_url = (
        f"http://127.0.0.1:8000/api/runs/{run_id}/publish-readiness"
    )
    request_body = _publication_proof_preflight_request_body()
    return [
        *_product_run_preflight_commands(run_id),
        (
            "curl -sS -X POST "
            f"{shlex.quote(publish_readiness_url)} "
            "-H 'Content-Type: application/json' "
            f"--data {shlex.quote(request_body)}"
        )
    ]


def _publication_proof_preflight_request_body(
    *,
    acknowledge_publish_channel_policy: bool = False,
) -> str:
    request_body = json.dumps(
        {
            "open_feedback_gate": False,
            "mark_run_completed_if_ready": False,
            "check_publish_channel_readiness": True,
            "acknowledge_publish_channel_policy": acknowledge_publish_channel_policy,
        },
        separators=(",", ":"),
    )
    return request_body


def _voice_proof_rejected_substitutes() -> list[str]:
    return [
        ".env.example placeholders",
        "OpenRouter credential existence without a live dialogue turn",
        "transcript rehearsal or local-only dry run",
        "credential existence without live calls",
    ]


def _publication_proof_rejected_substitutes() -> list[str]:
    return [
        "non-live channel smoke",
        "generic policy acknowledgement",
        "credential existence without destination proof",
        "local draft preview or generated artifact only",
    ]


def _voice_proof_linkage_requirements() -> list[str]:
    return [
        (
            "same run_id across runtime_health_ledger, provider_smoke_ledger, "
            "livekit_voice_timing_capture, and realtime_voice_timing_ledger"
        ),
        "voice_agent_process_start artifact captured before live smoke",
        (
            "same realtime_session_id or LiveKit room/session id across "
            "smoke, headless capture, timing, and participant evidence"
        ),
        (
            "required runtime checks appear in the preflight validation "
            "report's validated_runtime_checks"
        ),
        "runtime configuration snapshot recorded with the same checked_at",
    ]


def _publication_proof_linkage_requirements() -> list[str]:
    return [
        (
            "same run_id across publish-readiness, distribution package, "
            "approved artifact, and destination proof"
        ),
        (
            "destination_channel is linkedin and the preflight validation "
            "report's validated_publish_channels is exactly linkedin"
        ),
        "durable platform ID or URL matches the approved destination/channel",
        (
            "rollback or postcondition monitoring record references the same "
            "platform ID or URL"
        ),
    ]


def _voice_post_capture_validation_checks() -> list[str]:
    return [
        (
            "runtime_health_ledger voice-edge benchmark is ready and records "
            "p50/p95/max latency plus false-positive, missed-speech-start, "
            "and missed-cancellation counts"
        ),
        "provider_smoke_ledger execute_live_calls is true",
        "provider_smoke_ledger realtime_provider is openrouter_livekit",
        (
            "provider_smoke_ledger run_id equals realtime_voice_timing_ledger "
            "run_id and command_run_id"
        ),
        (
            "realtime_session_id or LiveKit room/session id matches across "
            "smoke, timing, and participant evidence"
        ),
        "first text or audio timing plus interruption evidence are present",
        "captured proof artifacts contain no token, API key, or secret values",
    ]


def _publication_post_capture_validation_checks() -> list[str]:
    return [
        (
            "publish-readiness, distribution package, approved artifact, and "
            "destination proof all reference command_run_id"
        ),
        (
            "destination_channel is linkedin and the preflight validation "
            "report's validated_publish_channels is exactly linkedin; durable "
            "URL is a LinkedIn destination"
        ),
        (
            "approved artifact snapshot has disclosure, visibility, audience, "
            "and schedule"
        ),
        (
            "platform API response or approved manual proof contains durable "
            "platform ID or URL"
        ),
        (
            "durable platform ID or URL matches rollback or postcondition "
            "monitoring record"
        ),
        "captured proof artifacts contain no token, API key, or secret values",
    ]


def _voice_failure_recording_requirements() -> list[str]:
    return [
        "record failing run_id and checked_at without secret values",
        (
            "record the failed preflight, runtime health, provider smoke, "
            "headless LiveKit capture, timing, managed voice-agent start, LiveKit, or "
            "participant-evidence step"
        ),
        (
            "record provider endpoint/account identifiers only after redacting "
            "tokens, API keys, and secrets"
        ),
        (
            "keep provider-backed-live-voice-proof blocked until a later "
            "same-session proof passes validation"
        ),
        "open or update the follow-up task with the failed validation check",
    ]


def _publication_failure_recording_requirements() -> list[str]:
    return [
        "record failing run_id and checked_at without secret values",
        (
            "record the failed publish-readiness, policy, approval, destination, "
            "or rollback/postcondition step"
        ),
        (
            "record platform response class, destination channel, and account "
            "identifier only after redacting tokens, API keys, and secrets"
        ),
        (
            "keep external-publication-proof blocked until a later exact-"
            "destination proof passes validation"
        ),
        "open or update the follow-up task with the failed validation check",
    ]


def _voice_success_recording_requirements() -> list[str]:
    return [
        "record passing run_id, checked_at, and validation timestamp",
        (
            "record voice_agent_process_start, runtime_health_ledger, "
            "provider_smoke_ledger, livekit_voice_timing_capture, "
            "realtime_voice_timing_ledger, LiveKit room/session id, and "
            "participant evidence artifact ids"
        ),
        (
            "record every post_capture_validation_check as passed before "
            "changing blocker state"
        ),
        (
            "update provider-backed-live-voice-proof status only after "
            "same-session validation passes"
        ),
        "close or link the follow-up task to the accepted proof record",
    ]


def _publication_success_recording_requirements() -> list[str]:
    return [
        "record passing run_id, checked_at, and validation timestamp",
        (
            "record publish-readiness, distribution package, approved artifact, "
            "destination proof, and rollback/postcondition artifact ids"
        ),
        (
            "record every post_capture_validation_check as passed before "
            "changing blocker state"
        ),
        (
            "update external-publication-proof status only after exact-"
            "destination validation passes"
        ),
        "close or link the follow-up task to the accepted proof record",
    ]


def _voice_proof_artifact_schema() -> dict[str, object]:
    return {
        "artifact_type": "provider_backed_live_voice_proof_record",
        "allowed_outcomes": ["accepted", "failed"],
        "state_field": "provider-backed-live-voice-proof",
        "required_fields": [
            "run_id",
            "checked_at",
            "validation_timestamp",
            "proof_outcome",
            "workspace_validation_report_artifact_id",
            "preflight_validation_report_artifact_id",
            "product_run_preflight_artifact_id",
            "provider_readiness_preflight_artifact_id",
            "voice_runtime_readiness_preflight_artifact_id",
            "voice_agent_process_start_artifact_id",
            "runtime_health_ledger_artifact_id",
            "voice_edge_benchmark_status",
            "provider_smoke_ledger_artifact_id",
            "livekit_voice_timing_capture_artifact_id",
            "realtime_voice_timing_ledger_artifact_id",
            "realtime_provider",
            "execute_live_calls",
            "realtime_session_id_or_livekit_room",
            "participant_identity",
            "runtime_configuration_snapshot_id",
            "post_capture_validation_results",
            "secret_redaction_check",
        ],
    }


def _publication_proof_artifact_schema() -> dict[str, object]:
    return {
        "artifact_type": "external_publication_proof_record",
        "allowed_outcomes": ["accepted", "failed"],
        "state_field": "external-publication-proof",
        "required_fields": [
            "run_id",
            "checked_at",
            "validation_timestamp",
            "proof_outcome",
            "workspace_validation_report_artifact_id",
            "preflight_validation_report_artifact_id",
            "product_run_preflight_artifact_id",
            "publish_readiness_preflight_artifact_id",
            "publish_readiness_artifact_id",
            "distribution_package_artifact_id",
            "approved_artifact_snapshot_id",
            "destination_channel",
            "durable_platform_id_or_url",
            "policy_acknowledgement_artifact_id",
            "rollback_or_postcondition_artifact_id",
            "post_capture_validation_results",
            "secret_redaction_check",
        ],
    }


def _provider_proof_plan_payload(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    credential_payload = _blocker_credential_snapshot_payload(
        args,
        env_values=env_values,
    )
    snapshots = credential_payload["snapshots"]
    voice_snapshot = snapshots["provider-backed-live-voice-proof"]
    publication_snapshot = snapshots["external-publication-proof"]
    run_id = args.run_id
    run_id_state = _proof_plan_run_id_state(run_id)
    product_run_id_state = _proof_plan_product_run_id_state(
        run_id,
        run_id_state=run_id_state,
    )
    command_run_id = _proof_plan_command_run_id(
        args.run_id,
        run_id_state=run_id_state,
    )
    command_run_id = _proof_product_run_id_command_value(
        command_run_id,
        product_run_id_state=product_run_id_state,
    )
    proof_output_dir = (
        Path("social_media_optimiser/output/provider-proof") / command_run_id
    )
    operator_input_readiness_report: dict[str, object] | None = None
    operator_input_path = getattr(args, "operator_input_path", None)
    if operator_input_path is not None:
        operator_input_readiness_report = (
            _provider_proof_operator_input_readiness_payload(
                argparse.Namespace(
                    env_example_path=args.env_example_path,
                    checked_at=credential_payload["checked_at"],
                    run_id=args.run_id,
                    input_path=Path(operator_input_path),
                )
            )
        )
    voice_status = _proof_plan_status(
        voice_snapshot,
        run_id_state=run_id_state,
        product_run_id_state=product_run_id_state,
    )
    voice_blocking_reasons = _proof_plan_blocking_reasons(
        voice_snapshot,
        run_id_state=run_id_state,
        product_run_id_state=product_run_id_state,
    )
    publication_status = _proof_plan_status(
        publication_snapshot,
        run_id_state=run_id_state,
        product_run_id_state=product_run_id_state,
    )
    publication_blocking_reasons = _proof_plan_blocking_reasons(
        publication_snapshot,
        run_id_state=run_id_state,
        product_run_id_state=product_run_id_state,
    )
    return {
        "artifact": "agent-studio-provider-proof-plan",
        "boundary": "planning_only_no_live_calls_no_secret_values",
        "checked_at": credential_payload["checked_at"],
        "credential_snapshot": credential_payload,
        "product_run_bootstrap": _product_run_bootstrap_handoff(),
        "proofs": {
            "provider-backed-live-voice-proof": {
                "status": voice_status,
                "blocking_reasons": voice_blocking_reasons,
                "credential_setup_requirements": (
                    PROVIDER_PROOF_CREDENTIAL_SETUP_REQUIREMENTS[
                        "provider-backed-live-voice-proof"
                    ]
                ),
                "credential_setup_commands": (
                    PROVIDER_PROOF_CREDENTIAL_SETUP_COMMANDS[
                        "provider-backed-live-voice-proof"
                    ]
                ),
                "operator_sequence": PROVIDER_PROOF_OPERATOR_SEQUENCE,
                "credential_state": voice_snapshot["state"],
                "configured_inputs": voice_snapshot["configured_inputs"],
                "configured_file_inputs": voice_snapshot[
                    "configured_file_inputs"
                ],
                "configured_local_provider_inputs": voice_snapshot[
                    "configured_local_provider_inputs"
                ],
                "local_provider_config_loaded": voice_snapshot[
                    "local_provider_config_loaded"
                ],
                "secret_files_loaded": voice_snapshot["secret_files_loaded"],
                "runtime_proof_required": True,
                "run_id_state": run_id_state,
                "product_run_id_state": product_run_id_state,
                "product_run_bootstrap": _product_run_bootstrap_handoff(),
                "run_id_required_before_execution": (
                    _run_id_required_before_execution()
                ),
                "command_run_id": command_run_id,
                "workspace_commands": _proof_workspace_commands(command_run_id),
                "workspace_validation_commands": (
                    _proof_workspace_validation_commands_for_output(
                        command_run_id,
                        Path(
                            "social_media_optimiser/output/provider-proof"
                        )
                        / command_run_id,
                    )
                ),
                "workspace_validation_report_files": (
                    _proof_workspace_validation_report_files(command_run_id)
                ),
                "workspace_validation_capture_commands": (
                    _proof_workspace_validation_capture_commands_for_output(
                        command_run_id,
                        Path(
                            "social_media_optimiser/output/provider-proof"
                        )
                        / command_run_id,
                    )
                ),
                "workspace_expected_files": _proof_workspace_expected_files(
                    command_run_id
                ),
                "attempt_gate": _proof_attempt_gate(
                    "provider-backed-live-voice-proof",
                    status=voice_status,
                    blocking_reasons=voice_blocking_reasons,
                    command_run_id=command_run_id,
                ),
                "commands": _proof_execution_commands(
                    "provider-backed-live-voice-proof",
                    command_run_id,
                ),
                "record_commands": _proof_record_commands(
                    "provider-backed-live-voice-proof",
                    command_run_id,
                    preflight_validation_path=(
                        _proof_preflight_validation_report_files(
                            "provider-backed-live-voice-proof",
                            command_run_id,
                        )[0]
                    ),
                    workspace_validation_path=(
                        _proof_workspace_validation_report_files(command_run_id)[0]
                    ),
                ),
                "template_commands": _proof_record_template_commands(
                    "provider-backed-live-voice-proof",
                    command_run_id,
                ),
                "completion_status_commands": _proof_completion_status_commands(
                    command_run_id
                ),
                "closeout_commands": _proof_closeout_commands(command_run_id),
                "preflight_checks": _voice_proof_preflight_checks(command_run_id),
                "preflight_commands": _voice_proof_preflight_commands(command_run_id),
                "preflight_output_files": _proof_preflight_output_files(
                    "provider-backed-live-voice-proof",
                    command_run_id,
                ),
                "preflight_capture_commands": _proof_preflight_capture_commands(
                    "provider-backed-live-voice-proof",
                    command_run_id,
                ),
                "preflight_artifact_id_fields": (
                    _proof_preflight_artifact_id_fields(
                        "provider-backed-live-voice-proof"
                    )
                ),
                "preflight_validation_commands": (
                    _proof_preflight_validation_commands(
                        "provider-backed-live-voice-proof",
                        command_run_id,
                    )
                ),
                "preflight_validation_report_files": (
                    _proof_preflight_validation_report_files(
                        "provider-backed-live-voice-proof",
                        command_run_id,
                    )
                ),
                "preflight_validation_requirements": (
                    _proof_preflight_validation_requirements(
                        "provider-backed-live-voice-proof"
                    )
                ),
                "preflight_validation_capture_commands": (
                    _proof_preflight_validation_capture_commands(
                        "provider-backed-live-voice-proof",
                        command_run_id,
                    )
                ),
                "proof_capture_commands_after_unblock": (
                    _provider_proof_capture_commands_after_unblock(
                        "provider-backed-live-voice-proof",
                        command_run_id,
                        Path(
                            "social_media_optimiser/output/provider-proof"
                        )
                        / command_run_id,
                    )
                ),
                "operator_proof_packet": _provider_proof_operator_packet_payload(
                    "provider-backed-live-voice-proof",
                    command_run_id,
                    proof_output_dir,
                    _voice_proof_artifact_schema(),
                    checked_at=str(credential_payload["checked_at"]),
                    operator_input_readiness=(
                        _provider_proof_operator_input_report_readiness(
                            "provider-backed-live-voice-proof",
                            operator_input_readiness_report,
                            checked_at=str(credential_payload["checked_at"]),
                            command_run_id=command_run_id,
                            output_dir=proof_output_dir,
                        )
                    ),
                ),
                "must_capture": [
                    "runtime_health_ledger with voice-edge-local-benchmark status ready",
                    "provider_smoke_ledger with execute_live_calls=true",
                    "livekit_voice_timing_capture JSON",
                    "realtime_voice_timing_ledger JSON",
                    "LiveKit room/session id and participant identity",
                    "captured microphone turn with first text/audio timing",
                    "interrupt or barge-in acknowledgement evidence",
                ],
                "rejected_substitutes": _voice_proof_rejected_substitutes(),
                "proof_linkage_requirements": (
                    _voice_proof_linkage_requirements()
                ),
                "post_capture_validation_checks": (
                    _voice_post_capture_validation_checks()
                ),
                "failure_recording_requirements": (
                    _voice_failure_recording_requirements()
                ),
                "success_recording_requirements": (
                    _voice_success_recording_requirements()
                ),
                "proof_artifact_schema": _voice_proof_artifact_schema(),
                "record_proof_in": PROVIDER_PROOF_RECORD_TARGETS,
                "unblock_when": _proof_plan_unblock_when(
                    [
                        "runtime_configuration_present_unverified",
                        "same-run runtime_health_ledger voice-edge benchmark is ready",
                        "same-session provider smoke succeeds with live calls",
                        "same-session realtime voice timing ledger is complete",
                    ],
                    run_id_state=run_id_state,
                    product_run_id_state=product_run_id_state,
                ),
            },
            "external-publication-proof": {
                "status": publication_status,
                "blocking_reasons": publication_blocking_reasons,
                "credential_setup_requirements": (
                    PROVIDER_PROOF_CREDENTIAL_SETUP_REQUIREMENTS[
                        "external-publication-proof"
                    ]
                ),
                "credential_setup_commands": (
                    PROVIDER_PROOF_CREDENTIAL_SETUP_COMMANDS[
                        "external-publication-proof"
                    ]
                ),
                "operator_sequence": PROVIDER_PROOF_OPERATOR_SEQUENCE,
                "credential_state": publication_snapshot["state"],
                "configured_inputs": publication_snapshot["configured_inputs"],
                "configured_file_inputs": publication_snapshot[
                    "configured_file_inputs"
                ],
                "configured_local_provider_inputs": publication_snapshot[
                    "configured_local_provider_inputs"
                ],
                "local_provider_config_loaded": publication_snapshot[
                    "local_provider_config_loaded"
                ],
                "secret_files_loaded": publication_snapshot[
                    "secret_files_loaded"
                ],
                "runtime_proof_required": True,
                "run_id_state": run_id_state,
                "product_run_id_state": product_run_id_state,
                "product_run_bootstrap": _product_run_bootstrap_handoff(),
                "run_id_required_before_execution": (
                    _run_id_required_before_execution()
                ),
                "command_run_id": command_run_id,
                "workspace_commands": _proof_workspace_commands(command_run_id),
                "workspace_validation_commands": (
                    _proof_workspace_validation_commands_for_output(
                        command_run_id,
                        Path(
                            "social_media_optimiser/output/provider-proof"
                        )
                        / command_run_id,
                    )
                ),
                "workspace_validation_report_files": (
                    _proof_workspace_validation_report_files(command_run_id)
                ),
                "workspace_validation_capture_commands": (
                    _proof_workspace_validation_capture_commands_for_output(
                        command_run_id,
                        Path(
                            "social_media_optimiser/output/provider-proof"
                        )
                        / command_run_id,
                    )
                ),
                "workspace_expected_files": _proof_workspace_expected_files(
                    command_run_id
                ),
                "attempt_gate": _proof_attempt_gate(
                    "external-publication-proof",
                    status=publication_status,
                    blocking_reasons=publication_blocking_reasons,
                    command_run_id=command_run_id,
                ),
                "commands": _proof_execution_commands(
                    "external-publication-proof",
                    command_run_id,
                ),
                "record_commands": _proof_record_commands(
                    "external-publication-proof",
                    command_run_id,
                    preflight_validation_path=(
                        _proof_preflight_validation_report_files(
                            "external-publication-proof",
                            command_run_id,
                        )[0]
                    ),
                    workspace_validation_path=(
                        _proof_workspace_validation_report_files(command_run_id)[0]
                    ),
                ),
                "template_commands": _proof_record_template_commands(
                    "external-publication-proof",
                    command_run_id,
                ),
                "completion_status_commands": _proof_completion_status_commands(
                    command_run_id
                ),
                "closeout_commands": _proof_closeout_commands(command_run_id),
                "preflight_checks": _publication_proof_preflight_checks(
                    command_run_id
                ),
                "preflight_commands": _publication_proof_preflight_commands(
                    command_run_id
                ),
                "preflight_output_files": _proof_preflight_output_files(
                    "external-publication-proof",
                    command_run_id,
                ),
                "preflight_capture_commands": _proof_preflight_capture_commands(
                    "external-publication-proof",
                    command_run_id,
                ),
                "preflight_artifact_id_fields": (
                    _proof_preflight_artifact_id_fields(
                        "external-publication-proof"
                    )
                ),
                "preflight_validation_commands": (
                    _proof_preflight_validation_commands(
                        "external-publication-proof",
                        command_run_id,
                    )
                ),
                "preflight_validation_report_files": (
                    _proof_preflight_validation_report_files(
                        "external-publication-proof",
                        command_run_id,
                    )
                ),
                "preflight_validation_requirements": (
                    _proof_preflight_validation_requirements(
                        "external-publication-proof"
                    )
                ),
                "preflight_validation_capture_commands": (
                    _proof_preflight_validation_capture_commands(
                        "external-publication-proof",
                        command_run_id,
                    )
                ),
                "proof_capture_commands_after_unblock": (
                    _provider_proof_capture_commands_after_unblock(
                        "external-publication-proof",
                        command_run_id,
                        Path(
                            "social_media_optimiser/output/provider-proof"
                        )
                        / command_run_id,
                    )
                ),
                "operator_proof_packet": _provider_proof_operator_packet_payload(
                    "external-publication-proof",
                    command_run_id,
                    proof_output_dir,
                    _publication_proof_artifact_schema(),
                    checked_at=str(credential_payload["checked_at"]),
                    operator_input_readiness=(
                        _provider_proof_operator_input_report_readiness(
                            "external-publication-proof",
                            operator_input_readiness_report,
                            checked_at=str(credential_payload["checked_at"]),
                            command_run_id=command_run_id,
                            output_dir=proof_output_dir,
                        )
                    ),
                ),
                "manual_capture_steps": [
                    "capture the exact destination policy acknowledgement",
                    (
                        "publish the approved artifact through the exact "
                        "platform API or approved manual channel"
                    ),
                    (
                        "verify the approved artifact snapshot includes "
                        "visibility, audience, disclosure, and schedule"
                    ),
                    "record the platform account identity without secret values",
                    "store the durable platform ID or URL in the audit notes",
                ],
                "must_capture": [
                    "approved artifact snapshot",
                    "disclosure-bearing approved artifact snapshot",
                    "channel policy acknowledgement",
                    "platform API response proof",
                    "durable platform ID or URL",
                    "postcondition monitoring record",
                    "rollback, delete, private, or correction proof",
                ],
                "rejected_substitutes": _publication_proof_rejected_substitutes(),
                "proof_linkage_requirements": (
                    _publication_proof_linkage_requirements()
                ),
                "post_capture_validation_checks": (
                    _publication_post_capture_validation_checks()
                ),
                "failure_recording_requirements": (
                    _publication_failure_recording_requirements()
                ),
                "success_recording_requirements": (
                    _publication_success_recording_requirements()
                ),
                "proof_artifact_schema": _publication_proof_artifact_schema(),
                "record_proof_in": PROVIDER_PROOF_RECORD_TARGETS,
                "unblock_when": _proof_plan_unblock_when(
                    [
                        "runtime_configuration_present_unverified",
                        "human-approved artifact and policy state are captured",
                        "exact destination proof is recorded",
                    ],
                    run_id_state=run_id_state,
                    product_run_id_state=product_run_id_state,
                ),
            },
        },
    }


def _print_provider_proof_plan(args: argparse.Namespace) -> None:
    payload = _provider_proof_plan_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_provider_proof_record_template(args: argparse.Namespace) -> None:
    payload = _provider_proof_record_template_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _provider_proof_operator_inputs_template() -> str:
    def template_status(field: str, value: str) -> tuple[str, str, str]:
        if (
            field == "OPENROUTER_LIVEKIT_URL"
            and value
            and not _provider_proof_record_template_placeholder(value)
        ):
            return (
                "configured",
                "none",
                "refresh_credential_snapshot",
            )
        if field in PROVIDER_PROOF_OPERATOR_INPUT_SECRET_FILE_FIELDS:
            return (
                "secret_file_unavailable",
                "operator_input_secret_file_unavailable",
                "write_readable_secret_file_and_reference_path",
            )
        return (
            "placeholder",
            "operator_input_placeholder",
            "replace_placeholder_in_operator_input_file",
        )

    def input_lines(field: str, value: str) -> list[str]:
        state, issue_code, next_action = template_status(field, value)
        return [
            f"# proof_id: {_provider_proof_operator_input_proof_id(field)}",
            f"# proof_input_role: {_provider_proof_operator_input_role(field)}",
            f"# contract: {PROVIDER_PROOF_OPERATOR_INPUT_FIELD_CONTRACTS[field]}",
            f"# value_source: {_provider_proof_operator_input_value_source(field)}",
            f"# template_state: {state}",
            f"# issue_code: {issue_code}",
            f"# next_action: {next_action}",
            f"{field}={value}",
        ]

    return "\n".join(
        [
            "# No-secret operator input template for UUID proof retry.",
            (
                "# Replace placeholders locally; do not commit real values or raw "
                "provider responses."
            ),
            "",
            "# Provider-backed live voice proof default inputs.",
            *input_lines("OPENROUTER_API_KEY_FILE", ".secrets/openrouter_api_key"),
            *input_lines("OPENROUTER_LIVEKIT_URL", "ws://127.0.0.1:7880"),
            *input_lines("LIVEKIT_API_KEY_FILE", ".secrets/livekit_api_key"),
            *input_lines("LIVEKIT_API_SECRET_FILE", ".secrets/livekit_api_secret"),
            "",
            "# External publication proof blockers.",
            *input_lines(
                "LINKEDIN_ACCESS_TOKEN_FILE",
                ".secrets/linkedin_access_token",
            ),
            *input_lines(
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
                "<artifact-id>",
            ),
            *input_lines(
                "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
                "<external-url-or-id>",
            ),
            *input_lines(
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
                "<artifact-id>",
            ),
            "",
        ]
    )


PROVIDER_PROOF_OPERATOR_INPUT_FIELDS = {
    "provider-backed-live-voice-proof": [
        "OPENROUTER_API_KEY_FILE",
        "OPENROUTER_LIVEKIT_URL",
        "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET_FILE",
    ],
    "external-publication-proof": [
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
    ],
}
PROVIDER_PROOF_OPERATOR_INPUT_SECRET_FILE_FIELDS = {
    "OPENROUTER_API_KEY_FILE",
    "LIVEKIT_API_KEY_FILE",
    "LIVEKIT_API_SECRET_FILE",
    "LINKEDIN_ACCESS_TOKEN_FILE",
}
PROVIDER_PROOF_OPERATOR_INPUT_URL_FIELDS = {
    "OPENROUTER_LIVEKIT_URL",
}
PROVIDER_PROOF_OPERATOR_INPUT_DESTINATION_FIELDS = {
    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
}
PROVIDER_PROOF_OPERATOR_INPUT_ARTIFACT_FIELDS = {
    "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
    "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
}
PROVIDER_PROOF_OPERATOR_INPUT_FIELD_CONTRACTS = {
    "OPENROUTER_API_KEY_FILE": (
        "readable local secret file path; file content is never emitted"
    ),
    "OPENROUTER_LIVEKIT_URL": (
        "ws or wss LiveKit URL for OpenRouter-backed realtime dialogue"
    ),
    "LIVEKIT_API_KEY_FILE": (
        "readable local secret file path; file content is never emitted"
    ),
    "LIVEKIT_API_SECRET_FILE": (
        "readable local secret file path; file content is never emitted"
    ),
    "LINKEDIN_ACCESS_TOKEN_FILE": (
        "readable local secret file path; file content is never emitted"
    ),
    "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID": (
        "durable non-local policy acknowledgement artifact id"
    ),
    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL": (
        "durable LinkedIn URL or platform id; local substitutes rejected"
    ),
    "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID": (
        "durable non-local rollback or postcondition artifact id"
    ),
}
PROVIDER_PROOF_OPERATOR_INPUT_FIELD_PROOF_IDS = {
    field: proof_name
    for proof_name, fields in PROVIDER_PROOF_OPERATOR_INPUT_FIELDS.items()
    for field in fields
}
PROVIDER_PROOF_OPERATOR_INPUT_FIELD_ROLES = {
    "OPENROUTER_API_KEY_FILE": "provider_credential",
    "OPENROUTER_LIVEKIT_URL": "transport_endpoint",
    "LIVEKIT_API_KEY_FILE": "transport_credential",
    "LIVEKIT_API_SECRET_FILE": "transport_credential",
    "LINKEDIN_ACCESS_TOKEN_FILE": "publisher_credential",
    "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID": "publication_evidence",
    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL": "publication_destination",
    "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID": "publication_evidence",
}


def _provider_proof_operator_input_field_contracts(
    proof_name: str,
) -> dict[str, str]:
    return {
        field: PROVIDER_PROOF_OPERATOR_INPUT_FIELD_CONTRACTS[field]
        for field in PROVIDER_PROOF_OPERATOR_INPUT_FIELDS.get(proof_name, [])
        if field in PROVIDER_PROOF_OPERATOR_INPUT_FIELD_CONTRACTS
    }


def _provider_proof_operator_input_field_ownership(
    proof_name: str,
) -> dict[str, dict[str, str]]:
    return {
        field: {
            "proof_id": _provider_proof_operator_input_proof_id(field),
            "proof_input_role": _provider_proof_operator_input_role(field),
        }
        for field in PROVIDER_PROOF_OPERATOR_INPUT_FIELDS.get(proof_name, [])
    }


def _provider_proof_operator_input_value_source(field: str) -> str:
    if field in PROVIDER_PROOF_OPERATOR_INPUT_SECRET_FILE_FIELDS:
        return "secret_file_path"
    if field in PROVIDER_PROOF_OPERATOR_INPUT_URL_FIELDS:
        return "endpoint_url"
    if field in PROVIDER_PROOF_OPERATOR_INPUT_DESTINATION_FIELDS:
        return "external_destination"
    if field in PROVIDER_PROOF_OPERATOR_INPUT_ARTIFACT_FIELDS:
        return "artifact_id"
    return "operator_input"


def _provider_proof_operator_input_proof_id(field: str) -> str:
    return PROVIDER_PROOF_OPERATOR_INPUT_FIELD_PROOF_IDS.get(field, "unknown")


def _provider_proof_operator_input_role(field: str) -> str:
    return PROVIDER_PROOF_OPERATOR_INPUT_FIELD_ROLES.get(field, "operator_input")


def _provider_proof_operator_input_field_status(
    field: str,
    *,
    state: str,
    issue_code: str,
    next_action: str,
) -> dict[str, str]:
    return {
        "state": state,
        "issue_code": issue_code,
        "proof_id": _provider_proof_operator_input_proof_id(field),
        "proof_input_role": _provider_proof_operator_input_role(field),
        "value_source": _provider_proof_operator_input_value_source(field),
        "next_action": next_action,
        "contract": PROVIDER_PROOF_OPERATOR_INPUT_FIELD_CONTRACTS.get(
            field,
            "operator input value",
        ),
    }


def _provider_proof_operator_input_field_status_markdown_key(key: str) -> str:
    if key == "proof_id":
        return "owner_proof_id"
    if key == "proof_input_role":
        return "owner_proof_input_role"
    return key


def _provider_proof_operator_input_field_statuses_from_groups(
    proof_name: str,
    proof: Mapping[str, object],
) -> dict[str, object]:
    configured_fields = proof.get("configured_fields", [])
    if not isinstance(configured_fields, list):
        configured_fields = []
    group_issue_actions = {
        "missing_fields": (
            "missing",
            "operator_input_missing",
            "set_field_in_operator_input_file",
        ),
        "placeholder_fields": (
            "placeholder",
            "operator_input_placeholder",
            "replace_placeholder_in_operator_input_file",
        ),
        "invalid_fields": (
            "invalid",
            "operator_input_invalid",
            "correct_operator_input_field",
        ),
        "unavailable_secret_file_fields": (
            "secret_file_unavailable",
            "operator_input_secret_file_unavailable",
            "write_readable_secret_file_and_reference_path",
        ),
    }
    field_statuses: dict[str, object] = {}
    for field in PROVIDER_PROOF_OPERATOR_INPUT_FIELDS.get(proof_name, []):
        field_status = None
        for group_name, (state, issue_code, next_action) in group_issue_actions.items():
            raw_fields = proof.get(group_name, [])
            if isinstance(raw_fields, list) and field in [str(item) for item in raw_fields]:
                field_status = _provider_proof_operator_input_field_status(
                    field,
                    state=state,
                    issue_code=issue_code,
                    next_action=next_action,
                )
                break
        if field_status is None:
            field_status = _provider_proof_operator_input_field_status(
                field,
                state=("configured" if field in configured_fields else "unknown"),
                issue_code="none",
                next_action="refresh_credential_snapshot",
            )
        field_statuses[field] = field_status
    return field_statuses


def _provider_proof_operator_input_effective_fail_exit_code(status: str) -> int:
    if status == "ready_for_credential_snapshot_refresh":
        return 0
    return 2


def _provider_proof_operator_input_next_action(
    proof_name: str,
    state: str,
    *,
    fallback: str,
    blocked_fields: Sequence[str] | None = None,
) -> str:
    if state == "ready_for_credential_snapshot_refresh":
        return "refresh_credential_snapshot"
    if state == "ready_for_preflight_capture":
        return "rerun_credential_snapshot_and_proof_plan"
    if proof_name == "provider-backed-live-voice-proof":
        blocked_field_set = {str(field) for field in blocked_fields or []}
        if blocked_field_set == {"OPENROUTER_API_KEY_FILE"}:
            return "supply_openrouter_api_key_file"
        if blocked_field_set == {"OPENROUTER_LIVEKIT_URL"}:
            return "supply_openrouter_livekit_url"
        if blocked_field_set == {"LIVEKIT_API_KEY_FILE", "LIVEKIT_API_SECRET_FILE"}:
            return "supply_livekit_key_and_secret_files"
        return "supply_openrouter_and_livekit_inputs"
    if proof_name == "external-publication-proof":
        return "supply_linkedin_token_policy_destination_and_rollback_evidence"
    return fallback


def _provider_proof_operator_input_required_evidence(
    proof_name: str,
) -> list[str]:
    shared = [
        "operator-input-readiness status ready_for_credential_snapshot_refresh",
        "credential-snapshot status runtime_configuration_present_unverified",
        "proof-plan attempt gate ready_for_preflight_capture",
    ]
    if proof_name == "provider-backed-live-voice-proof":
        return [
            *shared,
            "valid provider-backed live voice preflight validation",
            "same-run OpenRouter DeepSeek live dialogue reasoning evidence",
            "same-run realtime session or LiveKit room evidence",
            "provider smoke ledger evidence",
            "realtime voice timing ledger evidence",
            "zero failed post-capture validation checks",
            "passed secret-redaction check",
        ]
    if proof_name == "external-publication-proof":
        return [
            *shared,
            "valid external publication preflight validation",
            "destination channel and durable URL linked to validated linkedin readiness",
            "durable external destination proof",
            "policy acknowledgement artifact",
            "rollback or postcondition artifact",
            "zero failed post-capture validation checks",
            "passed secret-redaction check",
        ]
    return shared


def _provider_proof_operator_input_readiness_payload(
    args: argparse.Namespace,
) -> dict[str, object]:
    checked_at = args.checked_at or date.today().isoformat()
    input_path = args.input_path
    base_path = args.env_example_path.parent
    safe_input_path = _provider_proof_workspace_report_path_text(input_path)
    command_run_id = _proof_product_run_id_command_value(
        args.run_id,
        product_run_id_state=_proof_plan_product_run_id_state(
            args.run_id,
            run_id_state=_proof_plan_run_id_state(args.run_id),
        ),
    )
    base_payload = {
        "artifact": "agent-studio-provider-proof-operator-input-readiness",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": checked_at,
        "run_id": command_run_id,
        "input_path": safe_input_path,
        "state_change_allowed": False,
        "next_action_commands": _proof_operator_input_retry_commands_for_input(
            command_run_id,
            input_path,
        ),
        "guarded_next_action_commands": (
            _proof_operator_input_retry_commands_for_input(
                command_run_id,
                input_path,
                fail_on_blocked=True,
            )
        ),
        "exit_policy": {
            "default_exit_code": 0,
            "fail_on_blocked_exit_code": 2,
            "fail_on_blocked_statuses": [
                "blocked_by_operator_inputs",
                "invalid_operator_input_file",
            ],
            "ready_status": "ready_for_credential_snapshot_refresh",
        },
    }
    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(str(input_path)):
        return {
            **base_payload,
            "status": "invalid_operator_input_file",
            "effective_fail_on_blocked_exit_code": (
                _provider_proof_operator_input_effective_fail_exit_code(
                    "invalid_operator_input_file"
                )
            ),
            "next_action": "fix_operator_input_file",
            "issue_codes": ["operator_input_path_secret_shape_detected"],
            "issues": [
                {
                    "code": "operator_input_path_secret_shape_detected",
                    "field": "input_path",
                }
            ],
            "proofs": {},
        }
    if not input_path.exists():
        return {
            **base_payload,
            "status": "invalid_operator_input_file",
            "effective_fail_on_blocked_exit_code": (
                _provider_proof_operator_input_effective_fail_exit_code(
                    "invalid_operator_input_file"
                )
            ),
            "next_action": "fix_operator_input_file",
            "issue_codes": ["operator_input_file_missing"],
            "issues": [
                {
                    "code": "operator_input_file_missing",
                    "field": "input_path",
                }
            ],
            "proofs": {},
        }
    try:
        raw_text = input_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {
            **base_payload,
            "status": "invalid_operator_input_file",
            "effective_fail_on_blocked_exit_code": (
                _provider_proof_operator_input_effective_fail_exit_code(
                    "invalid_operator_input_file"
                )
            ),
            "next_action": "fix_operator_input_file",
            "issue_codes": ["operator_input_file_unreadable"],
            "issues": [
                {
                    "code": "operator_input_file_unreadable",
                    "field": "input_path",
                }
            ],
            "proofs": {},
        }
    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(raw_text):
        return {
            **base_payload,
            "status": "invalid_operator_input_file",
            "effective_fail_on_blocked_exit_code": (
                _provider_proof_operator_input_effective_fail_exit_code(
                    "invalid_operator_input_file"
                )
            ),
            "next_action": "fix_operator_input_file",
            "issue_codes": ["operator_input_secret_value_detected"],
            "issues": [
                {
                    "code": "operator_input_secret_value_detected",
                    "field": "input_path",
                }
            ],
            "proofs": {},
        }

    parsed_inputs = _env_example_items(input_path)
    issue_codes: list[str] = []
    issues: list[dict[str, object]] = []
    proof_payloads: dict[str, object] = {}
    for proof_name, required_fields in PROVIDER_PROOF_OPERATOR_INPUT_FIELDS.items():
        configured_fields: list[str] = []
        missing_fields: list[str] = []
        placeholder_fields: list[str] = []
        invalid_fields: list[str] = []
        unavailable_secret_file_fields: list[str] = []
        field_statuses: dict[str, object] = {}
        for field in required_fields:
            raw_value = parsed_inputs.get(field, "").strip()
            if not raw_value:
                missing_fields.append(field)
                field_statuses[field] = _provider_proof_operator_input_field_status(
                    field,
                    state="missing",
                    issue_code="operator_input_missing",
                    next_action="set_field_in_operator_input_file",
                )
                _provider_proof_add_issue(
                    issues,
                    issue_codes,
                    "operator_input_missing",
                    field,
                    f"{field} is missing",
                )
                continue
            if _provider_proof_record_template_placeholder(raw_value):
                placeholder_fields.append(field)
                field_statuses[field] = _provider_proof_operator_input_field_status(
                    field,
                    state="placeholder",
                    issue_code="operator_input_placeholder",
                    next_action="replace_placeholder_in_operator_input_file",
                )
                _provider_proof_add_issue(
                    issues,
                    issue_codes,
                    "operator_input_placeholder",
                    field,
                    f"{field} still has a placeholder value",
                )
                continue
            if field in PROVIDER_PROOF_OPERATOR_INPUT_URL_FIELDS:
                parsed_url = urlparse(raw_value)
                allowed_url_schemes = (
                    {"ws", "wss"}
                    if field == "OPENROUTER_LIVEKIT_URL"
                    else {"http", "https"}
                )
                if (
                    parsed_url.scheme not in allowed_url_schemes
                    or not parsed_url.netloc
                ):
                    invalid_fields.append(field)
                    field_statuses[field] = (
                        _provider_proof_operator_input_field_status(
                            field,
                            state="invalid",
                            issue_code="operator_input_invalid_url",
                            next_action="correct_operator_input_field",
                        )
                    )
                    _provider_proof_add_issue(
                        issues,
                        issue_codes,
                        "operator_input_invalid_url",
                        field,
                        f"{field} must be a {' or '.join(sorted(allowed_url_schemes))} URL",
                    )
                    continue
                is_substitute_url = (
                    _provider_proof_openrouter_livekit_url_is_placeholder(raw_value)
                    if field == "OPENROUTER_LIVEKIT_URL"
                    else _provider_proof_publication_destination_is_local_substitute(
                        raw_value
                    )
                )
                if is_substitute_url:
                    invalid_fields.append(field)
                    field_statuses[field] = (
                        _provider_proof_operator_input_field_status(
                            field,
                            state="invalid",
                            issue_code="operator_input_local_substitute",
                            next_action="correct_operator_input_field",
                        )
                    )
                    _provider_proof_add_issue(
                        issues,
                        issue_codes,
                        "operator_input_local_substitute",
                        field,
                        (
                            f"{field} must point to a concrete LiveKit URL"
                            if field == "OPENROUTER_LIVEKIT_URL"
                            else f"{field} must point to a non-local external URL"
                        ),
                    )
                    continue
            if (
                field in PROVIDER_PROOF_OPERATOR_INPUT_DESTINATION_FIELDS
                and _provider_proof_publication_destination_is_local_substitute(
                    raw_value
                )
            ):
                invalid_fields.append(field)
                field_statuses[field] = _provider_proof_operator_input_field_status(
                    field,
                    state="invalid",
                    issue_code="operator_input_local_substitute",
                    next_action="correct_operator_input_field",
                )
                _provider_proof_add_issue(
                    issues,
                    issue_codes,
                    "operator_input_local_substitute",
                    field,
                    f"{field} must point to a durable external destination",
                )
                continue
            if field in PROVIDER_PROOF_OPERATOR_INPUT_DESTINATION_FIELDS:
                platform = _provider_proof_publication_destination_platform(raw_value)
                if platform != "linkedin":
                    invalid_fields.append(field)
                    field_statuses[field] = (
                        _provider_proof_operator_input_field_status(
                            field,
                            state="invalid",
                            issue_code="operator_input_destination_channel_mismatch",
                            next_action="correct_operator_input_field",
                        )
                    )
                    _provider_proof_add_issue(
                        issues,
                        issue_codes,
                        "operator_input_destination_channel_mismatch",
                        field,
                        f"{field} must point to a LinkedIn destination",
                    )
                    continue
            if (
                field in PROVIDER_PROOF_OPERATOR_INPUT_ARTIFACT_FIELDS
                and _provider_proof_publication_destination_is_local_substitute(
                    raw_value
                )
            ):
                invalid_fields.append(field)
                field_statuses[field] = _provider_proof_operator_input_field_status(
                    field,
                    state="invalid",
                    issue_code="operator_input_local_artifact_substitute",
                    next_action="correct_operator_input_field",
                )
                _provider_proof_add_issue(
                    issues,
                    issue_codes,
                    "operator_input_local_artifact_substitute",
                    field,
                    f"{field} must reference a durable non-local artifact",
                )
                continue
            if field in PROVIDER_PROOF_OPERATOR_INPUT_SECRET_FILE_FIELDS:
                if PROVIDER_PROOF_OPERATOR_SECRET_PATH_PATTERN.search(raw_value):
                    invalid_fields.append(field)
                    field_statuses[field] = (
                        _provider_proof_operator_input_field_status(
                            field,
                            state="invalid",
                            issue_code="operator_input_secret_path_detected",
                            next_action="correct_operator_input_field",
                        )
                    )
                    _provider_proof_add_issue(
                        issues,
                        issue_codes,
                        "operator_input_secret_path_detected",
                        field,
                        f"{field} path contains secret-shaped text",
                    )
                    continue
                secret_path = Path(raw_value).expanduser()
                if not secret_path.is_absolute():
                    secret_path = base_path / secret_path
                try:
                    secret_text = secret_path.read_text(encoding="utf-8").strip()
                except (OSError, UnicodeError):
                    secret_text = ""
                if (
                    not secret_path.is_file()
                    or not secret_text
                    or _provider_proof_record_template_placeholder(secret_text)
                ):
                    unavailable_secret_file_fields.append(field)
                    field_statuses[field] = (
                        _provider_proof_operator_input_field_status(
                            field,
                            state="secret_file_unavailable",
                            issue_code="operator_input_secret_file_unavailable",
                            next_action=(
                                "write_readable_secret_file_and_reference_path"
                            ),
                        )
                    )
                    _provider_proof_add_issue(
                        issues,
                        issue_codes,
                        "operator_input_secret_file_unavailable",
                        field,
                        f"{field} file is missing, empty, or placeholder-only",
                    )
                    continue
            configured_fields.append(field)
            field_statuses[field] = _provider_proof_operator_input_field_status(
                field,
                state="configured",
                issue_code="none",
                next_action="refresh_credential_snapshot",
            )
        proof_state = (
            "ready_for_credential_snapshot_refresh"
            if len(configured_fields) == len(required_fields)
            else "blocked_by_operator_inputs"
        )
        blocked_fields = [
            field
            for field in required_fields
            if field not in configured_fields
        ]
        proof_payloads[proof_name] = {
            "state": proof_state,
            "required_fields": list(required_fields),
            "blocked_fields": blocked_fields,
            "field_contracts": _provider_proof_operator_input_field_contracts(
                proof_name
            ),
            "field_ownership": _provider_proof_operator_input_field_ownership(
                proof_name
            ),
            "field_statuses": field_statuses,
            "configured_fields": configured_fields,
            "missing_fields": missing_fields,
            "placeholder_fields": placeholder_fields,
            "invalid_fields": invalid_fields,
            "unavailable_secret_file_fields": unavailable_secret_file_fields,
        }

    status = (
        "ready_for_credential_snapshot_refresh"
        if all(
            proof["state"] == "ready_for_credential_snapshot_refresh"
            for proof in proof_payloads.values()
            if isinstance(proof, Mapping)
        )
        else "blocked_by_operator_inputs"
    )
    blocked_fields: list[str] = []
    required_fields: list[str] = []
    configured_fields: list[str] = []
    field_groups: dict[str, list[str]] = {
        "missing_fields": [],
        "placeholder_fields": [],
        "invalid_fields": [],
        "unavailable_secret_file_fields": [],
    }
    field_contracts: dict[str, str] = {}
    field_ownership: dict[str, object] = {}
    field_statuses: dict[str, object] = {}
    for proof_name in PROVIDER_PROOF_OPERATOR_INPUT_FIELDS:
        proof = proof_payloads.get(proof_name)
        if not isinstance(proof, Mapping):
            continue
        raw_required_fields = proof.get("required_fields", [])
        if isinstance(raw_required_fields, list):
            for raw_field in raw_required_fields:
                field = str(raw_field)
                if field and field not in required_fields:
                    required_fields.append(field)
        raw_field_contracts = proof.get("field_contracts", {})
        if isinstance(raw_field_contracts, Mapping):
            for raw_field, raw_contract in raw_field_contracts.items():
                field = str(raw_field)
                if field and field not in field_contracts:
                    field_contracts[field] = str(raw_contract)
        raw_field_ownership = proof.get("field_ownership", {})
        if isinstance(raw_field_ownership, Mapping):
            for raw_field, raw_ownership in raw_field_ownership.items():
                field = str(raw_field)
                if field and field not in field_ownership:
                    if isinstance(raw_ownership, Mapping):
                        field_ownership[field] = {
                            str(key): str(value)
                            for key, value in raw_ownership.items()
                        }
                    else:
                        field_ownership[field] = {
                            "proof_id": _provider_proof_operator_input_proof_id(
                                field
                            ),
                            "proof_input_role": (
                                _provider_proof_operator_input_role(field)
                            ),
                        }
        raw_field_statuses = proof.get("field_statuses", {})
        if isinstance(raw_field_statuses, Mapping):
            for raw_field, raw_status in raw_field_statuses.items():
                field = str(raw_field)
                if field and field not in field_statuses:
                    field_statuses[field] = raw_status
        raw_configured_fields = proof.get("configured_fields", [])
        if isinstance(raw_configured_fields, list):
            for raw_field in raw_configured_fields:
                field = str(raw_field)
                if field and field not in configured_fields:
                    configured_fields.append(field)
        for group_name in field_groups:
            raw_group_fields = proof.get(group_name, [])
            if not isinstance(raw_group_fields, list):
                continue
            for raw_field in raw_group_fields:
                field = str(raw_field)
                if field and field not in field_groups[group_name]:
                    field_groups[group_name].append(field)
        raw_blocked_fields = proof.get("blocked_fields", [])
        if not isinstance(raw_blocked_fields, list):
            continue
        for raw_field in raw_blocked_fields:
            field = str(raw_field)
            if field and field not in blocked_fields:
                blocked_fields.append(field)
    return {
        **base_payload,
        "status": status,
        "effective_fail_on_blocked_exit_code": (
            _provider_proof_operator_input_effective_fail_exit_code(status)
        ),
        "issue_codes": issue_codes,
        "issues": issues,
        "blocked_fields": blocked_fields,
        "required_fields": required_fields,
        "configured_fields": configured_fields,
        "field_groups": field_groups,
        "field_contracts": field_contracts,
        "field_ownership": field_ownership,
        "field_statuses": field_statuses,
        "proofs": proof_payloads,
        "next_action": (
            "refresh_credential_snapshot"
            if status == "ready_for_credential_snapshot_refresh"
            else "replace_placeholders_and_secret_file_paths"
        ),
    }


def _provider_proof_add_issue(
    issues: list[dict[str, object]],
    issue_codes: list[str],
    code: str,
    field: str,
    detail: str,
) -> None:
    issues.append({"code": code, "field": field, "detail": detail})
    if code not in issue_codes:
        issue_codes.append(code)


def _print_provider_proof_operator_input_readiness(args: argparse.Namespace) -> None:
    payload = _provider_proof_operator_input_readiness_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if getattr(args, "fail_on_blocked", False):
        raw_exit_code = payload.get("effective_fail_on_blocked_exit_code")
        exit_code = raw_exit_code if isinstance(raw_exit_code, int) else 2
        if exit_code:
            raise SystemExit(exit_code)


def _provider_proof_workspace_payload(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    proof_plan = _provider_proof_plan_payload(args, env_values=env_values)
    first_proof = next(iter(proof_plan["proofs"].values()))
    run_id_state = first_proof["run_id_state"]
    product_run_id_state = first_proof["product_run_id_state"]
    command_run_id = _proof_product_run_id_command_value(
        args.run_id,
        product_run_id_state=str(product_run_id_state),
    )
    output_dir = args.output_dir
    safe_output_dir = _provider_proof_output_path_text(output_dir)
    base_payload = {
        "artifact": "agent-studio-provider-proof-workspace",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": proof_plan["checked_at"],
        "run_id": command_run_id,
        "run_id_state": run_id_state,
        "product_run_id_state": product_run_id_state,
        "output_dir": safe_output_dir,
    }
    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(str(output_dir)):
        return {
            **base_payload,
            "status": "invalid_workspace",
            "issue_codes": ["workspace_path_secret_shape_detected"],
            "issues": [
                {
                    "code": "workspace_path_secret_shape_detected",
                    "field": safe_output_dir,
                    "detail": "output_dir contains token-shaped text",
                }
            ],
            "written_files": [],
        }
    if _provider_proof_workspace_path_has_non_directory_ancestor(output_dir):
        return {
            **base_payload,
            "status": "invalid_workspace",
            "issue_codes": ["workspace_path_unwritable"],
            "issues": [
                {
                    "code": "workspace_path_unwritable",
                    "field": safe_output_dir,
                    "detail": (
                        "output_dir or an existing ancestor is not a directory"
                    ),
                }
            ],
            "written_files": [],
        }
    if run_id_state != "concrete_run_id" or product_run_id_state != "product_run_uuid":
        issue_code = (
            "run_id_not_concrete"
            if run_id_state != "concrete_run_id"
            else "run_id_not_product_uuid"
        )
        issue_detail = (
            "replace <run-id> with a durable product run UUID before "
            "initializing proof workspace"
            if issue_code == "run_id_not_concrete"
            else (
                "replace run id with a durable product run UUID before "
                "initializing proof workspace"
            )
        )
        return {
            **base_payload,
            "status": "blocked_by_run_id",
            "next_action": "replace_run_id_and_initialize_workspace",
            "next_action_commands": _proof_workspace_commands_for_output(
                command_run_id,
                output_dir,
            ),
            "issue_codes": [issue_code],
            "issues": [
                {
                    "code": issue_code,
                    "field": "run_id",
                    "detail": issue_detail,
                }
            ],
            "written_files": [],
        }

    template_targets = [
        (proof_name, output_dir / f"{proof_name}.template.json")
        for proof_name in proof_plan["proofs"]
    ]
    operator_inputs_path = output_dir / "operator-inputs.template.env"
    readme_path = output_dir / "README.md"
    existing_files = [
        path
        for _, path in template_targets
        if path.exists()
    ]
    if operator_inputs_path.exists():
        existing_files.append(operator_inputs_path)
    if readme_path.exists():
        existing_files.append(readme_path)
    if existing_files:
        return {
            **base_payload,
            "status": "workspace_exists",
            "issue_codes": ["workspace_files_exist"],
            "issues": [
                {
                    "code": "workspace_files_exist",
                    "field": "output_dir",
                    "detail": (
                        "proof workspace target files already exist; choose a new "
                        "output directory before initializing"
                    ),
                }
            ],
            "existing_files": [str(path) for path in existing_files],
            "written_files": [],
        }

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return {
            **base_payload,
            "status": "invalid_workspace",
            "issue_codes": ["workspace_path_unwritable"],
            "issues": [
                {
                    "code": "workspace_path_unwritable",
                    "field": safe_output_dir,
                    "detail": (
                        "output_dir or an existing ancestor is not a directory"
                    ),
                }
            ],
            "written_files": [],
        }
    written_files: list[Path] = []
    template_payloads = []
    for proof_name, template_path in template_targets:
        template_payload = _provider_proof_record_template_payload(
            argparse.Namespace(
                env_example_path=args.env_example_path,
                checked_at=args.checked_at,
                run_id=args.run_id,
                proof=proof_name,
            ),
            env_values=env_values,
        )
        if template_payload["status"] != "template_ready":
            return {
                **base_payload,
                "status": template_payload["status"],
                "issue_codes": template_payload["issue_codes"],
                "issues": template_payload["issues"],
                "written_files": [str(path) for path in written_files],
            }
        template_path.write_text(
            json.dumps(template_payload["record"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written_files.append(template_path)
        template_payloads.append((proof_name, template_path, template_payload))

    operator_inputs_path.write_text(
        _provider_proof_operator_inputs_template(),
        encoding="utf-8",
    )
    written_files.append(operator_inputs_path)

    readme_path.write_text(
        _provider_proof_workspace_readme(
            proof_plan=proof_plan,
            template_payloads=template_payloads,
        ),
        encoding="utf-8",
    )
    written_files.append(readme_path)
    return {
        **base_payload,
        "status": "workspace_ready",
        "issue_codes": [],
        "issues": [],
        "validation_commands": _proof_workspace_validation_commands_for_output(
            str(first_proof["command_run_id"]),
            output_dir,
        ),
        "written_files": [str(path) for path in written_files],
    }


def _provider_proof_workspace_path_has_non_directory_ancestor(path: Path) -> bool:
    candidate = path
    while True:
        if os.path.lexists(candidate):
            return not candidate.is_dir()
        parent = candidate.parent
        if parent == candidate:
            return False
        candidate = parent


def _provider_proof_workspace_readme(
    *,
    proof_plan: Mapping[str, object],
    template_payloads: list[tuple[str, Path, Mapping[str, object]]],
) -> str:
    output_dir = _provider_proof_workspace_readme_path(template_payloads[0][1].parent)
    first_proof = next(iter(proof_plan["proofs"].values()))
    command_run_id = str(first_proof["command_run_id"])
    product_run_id_state = str(first_proof.get("product_run_id_state", "unknown"))
    product_run_gate_lines: list[str] = []
    if product_run_id_state != "product_run_uuid":
        bootstrap = proof_plan.get("product_run_bootstrap", {})
        bootstrap_commands: list[str] = []
        if isinstance(bootstrap, Mapping):
            raw_commands = bootstrap.get("commands", [])
            if isinstance(raw_commands, list):
                bootstrap_commands = [str(command) for command in raw_commands]
        product_run_gate_lines = [
            "## Product Run Gate",
            "",
            "- status: blocked_by_run_id",
            f"- product_run_id_state: {product_run_id_state}",
            "",
            "Do not run provider preflight until this workspace is tied to a durable product run UUID.",
            "",
            "Create or select a durable product run UUID first:",
            "",
            "- API path: `POST /api/runs`",
            *[f"- `{command}`" for command in bootstrap_commands],
            "",
        ]
    operator_input_retry_commands = [
        _proof_operator_input_readiness_capture_command(command_run_id, output_dir),
        (
            "uv run all-about-llms-admin blocker-credential-snapshot "
            f"--operator-input-path {output_dir}/operator-inputs.template.env > "
            f"{output_dir}/credential-snapshot.json"
        ),
        (
            "uv run all-about-llms-admin provider-proof-plan "
            f"--run-id {command_run_id} --operator-input-path "
            f"{output_dir}/operator-inputs.template.env > "
            f"{output_dir}/proof-plan.json"
        ),
        _proof_current_blocker_matrix_capture_command(command_run_id, output_dir),
        _proof_current_status_capture_command(command_run_id, output_dir),
        _proof_operator_unblocker_checklist_capture_command(
            command_run_id,
            output_dir,
        ),
    ]
    guarded_operator_input_retry_commands = [
        _proof_operator_input_readiness_capture_command(
            command_run_id,
            output_dir,
            fail_on_blocked=True,
        ),
        *operator_input_retry_commands[1:],
    ]
    aggregate_blocked_fields: list[str] = []
    aggregate_required_fields: list[str] = []
    aggregate_configured_fields: list[str] = []
    aggregate_field_contracts: dict[str, str] = {}
    aggregate_field_groups: dict[str, list[str]] = {
        "invalid_fields": [],
        "missing_fields": [],
        "placeholder_fields": [],
        "unavailable_secret_file_fields": [],
    }
    aggregate_field_ownership: dict[str, object] = {}
    aggregate_field_statuses: dict[str, object] = {}
    operator_route_lines = ["- per-proof operator input route commands:"]

    def readme_field_ownership_lines(
        ownership: Mapping[str, object],
        *,
        field_indent: str,
        ownership_indent: str,
    ) -> list[str]:
        if not ownership:
            return [f"{field_indent}`none`"]
        lines: list[str] = []
        for field, raw_ownership in ownership.items():
            lines.append(f"{field_indent}- {field}:")
            if not isinstance(raw_ownership, Mapping) or not raw_ownership:
                lines.append(f"{ownership_indent}- proof_id: `{raw_ownership}`")
                continue
            for ownership_key, ownership_value in raw_ownership.items():
                lines.append(
                    f"{ownership_indent}- {ownership_key}: `{ownership_value}`"
                )
        return lines

    def readme_field_status_lines(
        statuses: Mapping[str, object],
        *,
        field_indent: str,
        status_indent: str,
    ) -> list[str]:
        if not statuses:
            return [f"{field_indent}`none`"]
        lines: list[str] = []
        for field, raw_status in statuses.items():
            lines.append(f"{field_indent}- {field}:")
            if not isinstance(raw_status, Mapping) or not raw_status:
                lines.append(f"{status_indent}- state: `{raw_status}`")
                continue
            for status_key, status_value in raw_status.items():
                label = _provider_proof_operator_input_field_status_markdown_key(
                    str(status_key)
                )
                lines.append(f"{status_indent}- {label}: `{status_value}`")
        return lines

    operator_route_diagnostics = {
        "provider-backed-live-voice-proof": {
            "issue_codes": [
                "operator_input_secret_file_unavailable",
                "operator_input_placeholder",
            ],
            "field_groups": {
                "invalid_fields": [],
                "missing_fields": [],
                "placeholder_fields": ["OPENROUTER_LIVEKIT_URL"],
                "unavailable_secret_file_fields": [
                    "OPENROUTER_API_KEY_FILE",
                    "LIVEKIT_API_KEY_FILE",
                    "LIVEKIT_API_SECRET_FILE",
                ],
            },
        },
        "external-publication-proof": {
            "issue_codes": [
                "operator_input_secret_file_unavailable",
                "operator_input_placeholder",
            ],
            "field_groups": {
                "invalid_fields": [],
                "missing_fields": [],
                "placeholder_fields": [
                    "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
                    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
                    "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
                ],
                "unavailable_secret_file_fields": ["LINKEDIN_ACCESS_TOKEN_FILE"],
            },
        },
    }
    for proof_name in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        diagnostics = operator_route_diagnostics[proof_name]
        field_groups = diagnostics["field_groups"]
        proof_required_fields = [
            str(field)
            for field in PROVIDER_PROOF_OPERATOR_INPUT_FIELDS.get(proof_name, [])
        ]
        for field in proof_required_fields:
            if field and field not in aggregate_required_fields:
                aggregate_required_fields.append(field)
        proof_field_contracts = _provider_proof_operator_input_field_contracts(
            proof_name
        )
        for field, contract in proof_field_contracts.items():
            if field and field not in aggregate_field_contracts:
                aggregate_field_contracts[field] = contract
        proof_field_ownership = _provider_proof_operator_input_field_ownership(
            proof_name
        )
        for field, ownership in proof_field_ownership.items():
            if field and field not in aggregate_field_ownership:
                aggregate_field_ownership[field] = ownership
        proof_for_status = {
            **field_groups,
            "configured_fields": [],
        }
        proof_field_statuses = _provider_proof_operator_input_field_statuses_from_groups(
            proof_name,
            proof_for_status,
        )
        for field, status in proof_field_statuses.items():
            if field and field not in aggregate_field_statuses:
                aggregate_field_statuses[field] = status
        proof_field_contract_lines = [
            f"      - {field}: `{contract}`"
            for field, contract in proof_field_contracts.items()
        ] or ["      `none`"]
        proof_field_ownership_lines = readme_field_ownership_lines(
            proof_field_ownership,
            field_indent="      ",
            ownership_indent="        ",
        )
        proof_field_status_lines = readme_field_status_lines(
            proof_field_statuses,
            field_indent="      ",
            status_indent="        ",
        )
        proof_blocked_fields: list[str] = []
        field_group_lines: list[str] = []
        for group_name, fields in field_groups.items():
            field_group_lines.append(f"      - {group_name}:")
            if fields:
                field_group_lines.extend(f"        `{field}`" for field in fields)
            else:
                field_group_lines.append("        `none`")
            if group_name not in aggregate_field_groups:
                aggregate_field_groups[group_name] = []
            for field in fields:
                if field and field not in aggregate_field_groups[group_name]:
                    aggregate_field_groups[group_name].append(field)
                if field and field not in proof_blocked_fields:
                    proof_blocked_fields.append(field)
                if field and field not in aggregate_blocked_fields:
                    aggregate_blocked_fields.append(field)
        operator_route_lines.extend(
            [
                f"  - {proof_name}:",
                "    - status: `blocked_by_operator_inputs`",
                f"    - checked_at: `{proof_plan['checked_at']}`",
                "    - evidence_ref: `operator-input-readiness.json`",
                (
                    "    - next_action: "
                    "`"
                    + _provider_proof_operator_input_next_action(
                        proof_name,
                        "blocked_by_operator_inputs",
                        fallback="inspect_operator_input_readiness",
                        blocked_fields=proof_blocked_fields,
                    )
                    + "`"
                ),
                "    - effective_fail_on_blocked_exit_code: `2`",
                "    - blocked_fields:",
                *(
                    [f"      `{field}`" for field in proof_blocked_fields]
                    if proof_blocked_fields
                    else ["      `none`"]
                ),
                "    - required_fields:",
                *(
                    [f"      `{field}`" for field in proof_required_fields]
                    if proof_required_fields
                    else ["      `none`"]
                ),
                "    - configured_fields:",
                "      `none`",
                "    - field_contracts:",
                *proof_field_contract_lines,
                "    - field_ownership:",
                *proof_field_ownership_lines,
                "    - field_statuses:",
                *proof_field_status_lines,
                "    - issue_codes:",
                *[f"      `{code}`" for code in diagnostics["issue_codes"]],
                "    - field_groups:",
                *field_group_lines,
                "    - next_action_commands:",
                *[f"      `{command}`" for command in operator_input_retry_commands],
                "    - guarded_next_action_commands:",
                *[
                    f"      `{command}`"
                    for command in guarded_operator_input_retry_commands
                ],
            ]
        )
    aggregate_field_contract_lines = [
        f"    - {field}: `{contract}`"
        for field, contract in aggregate_field_contracts.items()
    ] or ["    `none`"]
    aggregate_field_ownership_lines = readme_field_ownership_lines(
        aggregate_field_ownership,
        field_indent="    ",
        ownership_indent="      ",
    )
    aggregate_field_status_lines: list[str] = []
    if aggregate_field_statuses:
        for field, raw_status in aggregate_field_statuses.items():
            aggregate_field_status_lines.append(f"    - {field}:")
            if not isinstance(raw_status, Mapping) or not raw_status:
                aggregate_field_status_lines.append(f"      - state: `{raw_status}`")
                continue
            for status_key, status_value in raw_status.items():
                label = _provider_proof_operator_input_field_status_markdown_key(
                    str(status_key)
                )
                aggregate_field_status_lines.append(
                    f"      - {label}: `{status_value}`"
                )
    else:
        aggregate_field_status_lines.append("    `none`")
    aggregate_readiness_lines = [
        "- aggregate operator input readiness:",
        "  - blocked_fields:",
        *(
            [f"    `{field}`" for field in aggregate_blocked_fields]
            if aggregate_blocked_fields
            else ["    `none`"]
        ),
        "  - required_fields:",
        *(
            [f"    `{field}`" for field in aggregate_required_fields]
            if aggregate_required_fields
            else ["    `none`"]
        ),
        "  - configured_fields:",
        *(
            [f"    `{field}`" for field in aggregate_configured_fields]
            if aggregate_configured_fields
            else ["    `none`"]
        ),
        "  - field_contracts:",
        *aggregate_field_contract_lines,
        "  - field_ownership:",
        *aggregate_field_ownership_lines,
        "  - field_groups:",
    ]
    for group_name, fields in aggregate_field_groups.items():
        aggregate_readiness_lines.append(f"    - {group_name}:")
        aggregate_readiness_lines.extend(
            [f"      `{field}`" for field in fields] if fields else ["      `none`"]
        )
    aggregate_readiness_lines.extend(
        [
            "  - field_statuses:",
            *aggregate_field_status_lines,
        ]
    )
    operator_readiness_by_proof: dict[str, object] = {}
    for proof_name in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        diagnostics = operator_route_diagnostics[proof_name]
        raw_field_groups = diagnostics["field_groups"]
        field_groups = (
            raw_field_groups
            if isinstance(raw_field_groups, Mapping)
            else {}
        )
        proof_for_status: dict[str, object] = {}
        blocked_fields: list[str] = []
        for group_name, raw_fields in field_groups.items():
            fields = raw_fields if isinstance(raw_fields, list) else []
            proof_for_status[group_name] = fields
            for raw_field in fields:
                field = str(raw_field)
                if field and field not in blocked_fields:
                    blocked_fields.append(field)
        proof_state = "blocked_by_operator_inputs"
        operator_readiness_by_proof[proof_name] = {
            "status": proof_state,
            "state": proof_state,
            "checked_at": str(proof_plan["checked_at"]),
            "evidence_ref": "operator-input-readiness.json",
            "next_action": _provider_proof_operator_input_next_action(
                proof_name,
                proof_state,
                fallback="inspect_operator_input_readiness",
                blocked_fields=blocked_fields,
            ),
            "effective_fail_on_blocked_exit_code": (
                _provider_proof_operator_input_effective_fail_exit_code(
                    proof_state,
                )
            ),
            "issue_codes": diagnostics["issue_codes"],
            "field_groups": field_groups,
            "field_contracts": _provider_proof_operator_input_field_contracts(
                proof_name,
            ),
            "field_ownership": _provider_proof_operator_input_field_ownership(
                proof_name,
            ),
            "field_statuses": (
                _provider_proof_operator_input_field_statuses_from_groups(
                    proof_name,
                    proof_for_status,
                )
            ),
            "next_action_commands": operator_input_retry_commands,
            "guarded_next_action_commands": guarded_operator_input_retry_commands,
            "blocked_fields": blocked_fields,
            "required_evidence_after_unblock": (
                _provider_proof_operator_input_required_evidence(proof_name)
            ),
        }
    operator_evidence_lines = ["- required evidence after input unblock:"]
    for proof_name in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        operator_evidence_lines.append(f"  - {proof_name}:")
        operator_evidence_lines.extend(
            [
                f"    - `{evidence}`"
                for evidence in _provider_proof_operator_input_required_evidence(
                    proof_name
                )
            ]
        )
    lines = [
        "# Provider Proof Workspace",
        "",
        f"- checked_at: {proof_plan['checked_at']}",
        "- boundary: no_secret_values_printed_no_state_change",
        "",
        "Fill these template files only with redacted artifact identifiers and validation results. Do not paste tokens, API keys, secret file contents, raw provider responses, or private audio.",
        "Run these commands from the repository root.",
        "",
        *product_run_gate_lines,
        "## Operator Input Template",
        "",
        f"- template: `{output_dir}/operator-inputs.template.env`",
        (
            "- fill placeholders locally; do not paste secrets into generated "
            "proof records."
        ),
        "- validate filled inputs before refreshing snapshots:",
        f"  `{_proof_operator_input_readiness_capture_command(command_run_id, output_dir)}`",
        "- strict automation readiness gate:",
        (
            "  `"
            f"{_proof_operator_input_readiness_capture_command(command_run_id, output_dir, fail_on_blocked=True)}"
            "`"
        ),
        "- refresh no-secret credential state from the filled input file:",
        (
            "  `uv run all-about-llms-admin blocker-credential-snapshot "
            f"--operator-input-path {output_dir}/operator-inputs.template.env > "
            f"{output_dir}/credential-snapshot.json`"
        ),
        "- refresh the proof plan from the filled input file:",
        (
            "  `uv run all-about-llms-admin provider-proof-plan "
            f"--run-id {command_run_id} --operator-input-path "
            f"{output_dir}/operator-inputs.template.env > "
            f"{output_dir}/proof-plan.json`"
        ),
        "- guarded retry sequence:",
        "  ```sh",
        *[f"  {command}" for command in guarded_operator_input_retry_commands],
        "  ```",
        *aggregate_readiness_lines,
        *operator_route_lines,
        *operator_evidence_lines,
        "",
        "Before preflight capture, validate this workspace still matches the current proof plan:",
        f"`{_proof_workspace_validation_commands_for_output(command_run_id, output_dir)[0]}`",
        "Capture that validation report for both proof records:",
        f"`{_proof_workspace_validation_capture_commands_for_output(command_run_id, output_dir)[0]}`",
        "",
    ]
    for proof_name, template_path, template_payload in template_payloads:
        proof = proof_plan["proofs"][proof_name]
        output_dir = _provider_proof_workspace_readme_path(template_path.parent)
        run_id = str(proof["command_run_id"])
        proof_output_dir = output_dir
        if str(proof.get("product_run_id_state", "unknown")) != "product_run_uuid":
            proof_output_dir = Path(f"social_media_optimiser/output/provider-proof/{run_id}")
        proof_artifact_schema = proof.get("proof_artifact_schema", {})
        proof_record_schema_lines: list[str] = []
        proof_record_required_fields: list[str] = []
        if isinstance(proof_artifact_schema, Mapping):
            raw_allowed_outcomes = proof_artifact_schema.get("allowed_outcomes")
            allowed_outcome_lines = (
                [f"    `{outcome}`" for outcome in raw_allowed_outcomes]
                if isinstance(raw_allowed_outcomes, list) and raw_allowed_outcomes
                else ["    `none`"]
            )
            proof_record_schema_lines = [
                "- proof_record_schema:",
                (
                    "  - artifact_type: "
                    f"`{proof_artifact_schema.get('artifact_type', 'unknown')}`"
                ),
                "  - allowed_outcomes:",
                *allowed_outcome_lines,
                (
                    "  - state_field: "
                    f"`{proof_artifact_schema.get('state_field', 'unknown')}`"
                ),
            ]
            raw_required_fields = proof_artifact_schema.get("required_fields", [])
            if isinstance(raw_required_fields, list):
                proof_record_required_fields = [
                    str(field) for field in raw_required_fields
                ]
        preflight_output_files = _proof_preflight_output_files_for_output(
            proof_name,
            proof_output_dir,
        )
        preflight_capture_commands = _proof_preflight_capture_commands_for_output(
            proof_name,
            run_id,
            proof_output_dir,
        )
        proof_capture_commands_after_unblock = (
            _provider_proof_capture_commands_after_unblock(
                proof_name,
                run_id,
                proof_output_dir,
            )
        )
        preflight_validation_commands = (
            _proof_preflight_validation_commands_for_output(
                proof_name,
                run_id,
                proof_output_dir,
            )
        )
        preflight_validation_report_files = (
            _proof_preflight_validation_report_files_for_output(
                proof_name,
                proof_output_dir,
            )
        )
        preflight_validation_capture_commands = (
            _proof_preflight_validation_capture_commands_for_output(
                proof_name,
                run_id,
                proof_output_dir,
            )
        )
        workspace_validation_report_files = (
            _proof_workspace_validation_report_files_for_output(proof_output_dir)
        )
        record_next_commands = _proof_record_next_commands(
            proof_name,
            run_id,
            preflight_validation_path=preflight_validation_report_files[0],
            workspace_validation_path=workspace_validation_report_files[0],
        )
        lines.extend(
            [
                f"## {proof_name}",
                "",
                f"- template: `{template_path.name}`",
                "- credential setup requirements:",
                *[
                    f"  {requirement}"
                    for requirement in proof["credential_setup_requirements"]
                ],
                "- credential setup commands:",
                *[
                    f"  `{command}`"
                    for command in proof["credential_setup_commands"]
                ],
                "- attempt gate:",
                f"  state: {proof['attempt_gate']['state']}",
                (
                    "  can_run_preflight_capture: "
                    f"{str(proof['attempt_gate']['can_run_preflight_capture']).lower()}"
                ),
                f"  next_action: {proof['attempt_gate']['next_action']}",
                "  proof commands allowed after:",
                *[
                    f"    {requirement}"
                    for requirement in proof["attempt_gate"][
                        "proof_commands_allowed_after"
                    ]
                ],
                "- preflight output files:",
                *[f"  `{path}`" for path in preflight_output_files],
                "- preflight commands:",
                *[f"  `{command}`" for command in proof["preflight_commands"]],
                "- preflight capture commands:",
                *[f"  `{command}`" for command in preflight_capture_commands],
                *_provider_proof_operator_packet_markdown_section(
                    {
                        **_provider_proof_operator_packet_readme_contract(
                            proof_name
                        ),
                        "proof_id": proof_name,
                        "matrix_parity_ref": (
                            f"/operator_input_readiness/proofs/{proof_name}"
                        ),
                        "proof_capture_matrix_ref": (
                            f"/proofs/{proof_name}/proof_capture_commands_after_unblock"
                        ),
                        "proof_capture_commands_after_unblock": (
                            proof_capture_commands_after_unblock
                        ),
                        "completion_evidence_ref": "completion-status.json",
                        "closure_evidence_refs": [
                            "closure-review-template.json",
                            "closure-review-status.json",
                            "blocker-state-update.json",
                        ],
                        "proof_record_schema": dict(proof_artifact_schema),
                        "proof_record_required_fields": (
                            proof_record_required_fields
                        ),
                        "proof_plan_packet": "proof-plan.json",
                        "proof_plan_packet_ref": str(
                            output_dir / "proof-plan.json"
                        ),
                        "proof_plan_packet_command": (
                            "uv run all-about-llms-admin provider-proof-plan "
                            f"--run-id {command_run_id} --operator-input-path "
                            f"{_proof_command_arg(output_dir / 'operator-inputs.template.env')} "
                            f"> {_proof_command_arg(output_dir / 'proof-plan.json')}"
                        ),
                        "proof_plan_operator_packet_ref": (
                            f"/proofs/{proof_name}/operator_proof_packet"
                        ),
                        "current_matrix_packet": "current-blocker-matrix.json",
                        "current_matrix_packet_ref": str(
                            output_dir / "current-blocker-matrix.json"
                        ),
                        "current_matrix_packet_command": (
                            _proof_current_blocker_matrix_capture_command(
                                command_run_id,
                                output_dir,
                            )
                        ),
                        "current_matrix_operator_packet_ref": (
                            f"/operator_proof_packets/{proof_name}"
                        ),
                        "operator_input_readiness": (
                            operator_readiness_by_proof[proof_name]
                        ),
                    }
                ),
                *proof_record_schema_lines,
                "- proof_record_required_fields:",
                *[f"  `{field}`" for field in proof_record_required_fields],
                "- proof_capture_commands_after_unblock:",
                *[
                    f"  `{command}`"
                    for command in proof_capture_commands_after_unblock
                ],
                "- validate preflight artifacts:",
                *[f"  `{command}`" for command in preflight_validation_commands],
                "- preflight validation report files:",
                *[f"  `{path}`" for path in preflight_validation_report_files],
                "- workspace validation report files:",
                *[f"  `{path}`" for path in workspace_validation_report_files],
                "- preflight validation requirements:",
                *[
                    f"  {requirement}"
                    for requirement in proof["preflight_validation_requirements"]
                ],
                "- write preflight validation report:",
                *[
                    f"  `{command}`"
                    for command in preflight_validation_capture_commands
                ],
                "- validate:",
                f"  `{record_next_commands[0]}`",
                "- record after validation:",
                f"  `{record_next_commands[1]}`",
                "",
            ]
        )
    run_id = str(first_proof["command_run_id"])
    lines.extend(
        [
            "## Completion status",
            "",
            "After recording both accepted proof records, check the audit targets:",
            (
                "`uv run all-about-llms-admin provider-proof-completion-status "
                f"--run-id {run_id}`"
            ),
            "",
            "## Current blocker handoff",
            "",
            "Regenerate the no-secret current-state handoff after each proof attempt:",
            "- current blocker matrix:",
            f"  `{_proof_current_blocker_matrix_capture_command(run_id, output_dir)}`",
            "- current proof status:",
            f"  `{_proof_current_status_capture_command(run_id, output_dir)}`",
            "- operator unblocker checklist:",
            f"  `{_proof_operator_unblocker_checklist_capture_command(run_id, output_dir)}`",
            "",
            "## Closure review and blocker update",
            "",
            "Only continue when completion status is `required_proofs_accepted`.",
            "- create closure-review template:",
            f"  `{_proof_closure_review_template_commands(run_id)[0]}`",
            "- validate filled closure-review record:",
            f"  `{_proof_closure_review_validation_commands(run_id)[0]}`",
            "- record approved or rejected closure review:",
            f"  `{_proof_closure_review_record_commands(run_id)[0]}`",
            "- check closure-review status:",
            f"  `{_proof_closure_review_status_commands(run_id)[0]}`",
            "- record reviewed blocker-state update note:",
            f"  `{_proof_blocker_state_update_record_commands(run_id)[0]}`",
            "",
            "`record-provider-proof-blocker-state-update` records `goal_completion_claimed=false`; it does not mark the active objective complete.",
            "",
        ]
    )
    return "\n".join(lines)


def _provider_proof_workspace_readme_path(path: Path) -> Path:
    try:
        relative_path = path.resolve().relative_to(PROJECT_ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        return path
    return Path(relative_path.as_posix())


def _print_provider_proof_workspace(args: argparse.Namespace) -> None:
    payload = _provider_proof_workspace_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _provider_proof_workspace_validation_payload(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    output_dir = args.output_dir
    operator_input_path = _provider_proof_workspace_operator_input_path(
        args,
        output_dir,
    )
    plan_args = argparse.Namespace(
        env_example_path=args.env_example_path,
        checked_at=args.checked_at,
        run_id=args.run_id,
        output_dir=output_dir,
        operator_input_path=operator_input_path,
    )
    proof_plan = _provider_proof_plan_payload(plan_args, env_values=env_values)
    first_proof = next(iter(proof_plan["proofs"].values()))
    run_id = str(first_proof["command_run_id"])
    run_id_state = first_proof["run_id_state"]
    product_run_id_state = first_proof["product_run_id_state"]
    safe_output_dir = _provider_proof_workspace_report_path_text(output_dir)
    base_payload = {
        "artifact": "agent-studio-provider-proof-workspace-validation",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": proof_plan["checked_at"],
        "run_id": run_id,
        "run_id_state": run_id_state,
        "product_run_id_state": product_run_id_state,
        "output_dir": safe_output_dir,
        "state_change_allowed": False,
    }
    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(str(output_dir)):
        return {
            **base_payload,
            "status": "invalid_workspace",
            "issue_codes": ["workspace_path_secret_shape_detected"],
            "issues": [
                {
                    "code": "workspace_path_secret_shape_detected",
                    "field": "output_dir",
                    "detail": "output_dir contains token-shaped text",
                }
            ],
            "expected_files": [],
            "validated_files": [],
        }
    if run_id_state != "concrete_run_id" or product_run_id_state != "product_run_uuid":
        issue_code = (
            "run_id_not_concrete"
            if run_id_state != "concrete_run_id"
            else "run_id_not_product_uuid"
        )
        issue_detail = (
            "replace <run-id> with a durable product run UUID before "
            "validating proof workspace"
            if issue_code == "run_id_not_concrete"
            else (
                "replace run id with a durable product run UUID before "
                "validating proof workspace"
            )
        )
        return {
            **base_payload,
            "status": "blocked_by_run_id",
            "issue_codes": [issue_code],
            "issues": [
                {
                    "code": issue_code,
                    "field": "run_id",
                    "detail": issue_detail,
                }
            ],
            "expected_files": [],
            "validated_files": [],
        }

    expected_files: dict[Path, str] = {}
    template_payloads = []
    issues: list[dict[str, object]] = []
    issue_codes: list[str] = []

    for proof_name in proof_plan["proofs"]:
        template_path = output_dir / f"{proof_name}.template.json"
        template_payload = _provider_proof_record_template_payload(
            argparse.Namespace(
                env_example_path=args.env_example_path,
                checked_at=args.checked_at,
                run_id=args.run_id,
                proof=proof_name,
                operator_input_path=operator_input_path,
            ),
            env_values=env_values,
        )
        if template_payload["status"] != "template_ready":
            issues.extend(template_payload["issues"])
            issue_codes.extend(template_payload["issue_codes"])
            continue
        expected_files[template_path] = (
            json.dumps(template_payload["record"], indent=2, sort_keys=True) + "\n"
        )
        template_payloads.append((proof_name, template_path, template_payload))

    operator_inputs_path = output_dir / "operator-inputs.template.env"
    expected_files[operator_inputs_path] = _provider_proof_operator_inputs_template()

    readme_path = output_dir / "README.md"
    expected_files[readme_path] = _provider_proof_workspace_readme(
        proof_plan=proof_plan,
        template_payloads=template_payloads,
    )
    validated_files: list[str] = []
    for path, expected_content in expected_files.items():
        if not path.exists():
            issues.append(
                {
                    "code": "workspace_file_missing",
                    "field": _provider_proof_workspace_report_path_text(path),
                    "detail": "workspace file is missing",
                }
            )
            issue_codes.append("workspace_file_missing")
            continue
        try:
            actual_content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            issues.append(
                {
                    "code": "workspace_file_unreadable",
                    "field": _provider_proof_workspace_report_path_text(path),
                    "detail": "workspace file is unreadable as UTF-8",
                }
            )
            issue_codes.append("workspace_file_unreadable")
            continue
        if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(actual_content):
            issues.append(
                {
                    "code": "workspace_file_secret_shape_detected",
                    "field": _provider_proof_workspace_report_path_text(path),
                    "detail": "workspace file contains token-shaped content",
                }
            )
            issue_codes.append("workspace_file_secret_shape_detected")
            continue
        if actual_content != expected_content:
            issues.append(
                {
                    "code": "workspace_file_mismatch",
                    "field": _provider_proof_workspace_report_path_text(path),
                    "detail": "workspace file does not match the current proof plan",
                }
            )
            issue_codes.append("workspace_file_mismatch")
            continue
        validated_files.append(_provider_proof_workspace_report_path_text(path))

    unique_issue_codes = list(dict.fromkeys(issue_codes))
    return {
        **base_payload,
        "status": "invalid_workspace" if unique_issue_codes else "valid_workspace",
        "issue_codes": unique_issue_codes,
        "issues": issues,
        "expected_files": [
            _provider_proof_workspace_report_path_text(path)
            for path in expected_files
        ],
        "validated_files": validated_files,
    }


def _provider_proof_workspace_operator_input_path(
    args: argparse.Namespace,
    output_dir: Path,
) -> Path | None:
    raw_path = getattr(args, "operator_input_path", None)
    if raw_path is not None:
        return Path(raw_path)
    candidate = output_dir / "operator-inputs.template.env"
    return candidate if candidate.exists() else None


def _print_provider_proof_workspace_validation(args: argparse.Namespace) -> None:
    payload = _provider_proof_workspace_validation_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _provider_proof_record_secret_paths(
    value: object,
    *,
    path: str = "$",
) -> list[str]:
    if isinstance(value, Mapping):
        paths: list[str] = []
        for index, (key, item) in enumerate(value.items()):
            key_text = str(key)
            key_path = (
                f"{path}.<redacted-key-{index}>"
                if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(key_text)
                else f"{path}.{key_text}"
            )
            if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(key_text):
                paths.append(key_path)
            paths.extend(
                _provider_proof_record_secret_paths(
                    item,
                    path=key_path,
                )
            )
        return paths
    if isinstance(value, list):
        paths = []
        for index, item in enumerate(value):
            paths.extend(
                _provider_proof_record_secret_paths(
                    item,
                    path=f"{path}[{index}]",
                )
            )
        return paths
    if isinstance(value, str) and PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(value):
        return [path]
    return []


def _provider_proof_output_path_text(value: object) -> str:
    text = str(value)
    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(text):
        return PROVIDER_PROOF_SECRET_VALUE_PATTERN.sub("<redacted>", text)
    return text


def _provider_proof_portable_path_text(value: object) -> str:
    text = _provider_proof_output_path_text(value)
    try:
        path = Path(str(value))
        relative_path = path.resolve().relative_to(PROJECT_ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        return text

    relative_text = relative_path.as_posix()
    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(relative_text):
        relative_text = PROVIDER_PROOF_SECRET_VALUE_PATTERN.sub(
            "<redacted>",
            relative_text,
        )
    if not relative_text:
        return "<workspace-root>"
    return f"<workspace-root>/{relative_text}"


def _provider_proof_workspace_report_path_text(value: object) -> str:
    return _provider_proof_portable_path_text(value)


def _provider_proof_record_template_payload(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    proof_plan = _provider_proof_plan_payload(args, env_values=env_values)
    proof_name = args.proof
    proofs = proof_plan["proofs"]
    if proof_name not in proofs:
        return {
            "artifact": "agent-studio-provider-proof-record-template",
            "boundary": "no_secret_values_printed_no_state_change",
            "checked_at": proof_plan["checked_at"],
            "proof": proof_name,
            "status": "invalid_proof",
            "issue_codes": ["unknown_proof"],
            "issues": [{"code": "unknown_proof", "field": "proof"}],
            "record": None,
        }

    proof = proofs[proof_name]
    schema = proof["proof_artifact_schema"]
    preflight_report_files = proof.get("preflight_validation_report_files")
    preflight_validation_path: object = "<preflight-validation.json>"
    if isinstance(preflight_report_files, list) and preflight_report_files:
        preflight_validation_path = preflight_report_files[0]
    workspace_report_files = proof.get("workspace_validation_report_files")
    workspace_validation_path: object = "<workspace-validation.json>"
    if isinstance(workspace_report_files, list) and workspace_report_files:
        workspace_validation_path = workspace_report_files[0]
    base_payload = {
        "artifact": "agent-studio-provider-proof-record-template",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": proof_plan["checked_at"],
        "proof": proof_name,
        "command_run_id": proof["command_run_id"],
        "run_id_state": proof["run_id_state"],
        "product_run_id_state": proof["product_run_id_state"],
        "proof_artifact_schema": schema,
        "post_capture_validation_checks": proof["post_capture_validation_checks"],
        "template_commands": proof["template_commands"],
        "next_commands": _proof_record_next_commands(
            proof_name,
            str(proof["command_run_id"]),
            preflight_validation_path=preflight_validation_path,
            workspace_validation_path=workspace_validation_path,
        ),
    }
    if proof["run_id_state"] != "concrete_run_id":
        return {
            **base_payload,
            "status": "blocked_by_run_id",
            "issue_codes": ["run_id_not_concrete"],
            "issues": [
                {
                    "code": "run_id_not_concrete",
                    "field": "run_id",
                    "detail": (
                        "replace <run-id> with a durable product run UUID before "
                        "capturing provider proof"
                    ),
                }
            ],
            "next_commands": [],
            "record": None,
        }
    if proof["product_run_id_state"] != "product_run_uuid":
        return {
            **base_payload,
            "status": "blocked_by_run_id",
            "issue_codes": ["run_id_not_product_uuid"],
            "issues": [
                {
                    "code": "run_id_not_product_uuid",
                    "field": "run_id",
                    "detail": (
                        "provider proof records require a durable product run "
                        "UUID before capture"
                    ),
                }
            ],
            "next_commands": [],
            "record": None,
        }

    required_fields = schema["required_fields"]
    if not isinstance(required_fields, list):
        raise TypeError("proof_artifact_schema required_fields must be a list")
    record = {
        str(field): _provider_proof_record_template_value(
            proof_name,
            str(field),
            proof=proof,
            checked_at=str(proof_plan["checked_at"]),
        )
        for field in required_fields
    }
    return {
        **base_payload,
        "status": "template_ready",
        "issue_codes": [],
        "issues": [],
        "record": record,
    }


def _provider_proof_record_template_value(
    proof_name: str,
    field: str,
    *,
    proof: Mapping[str, object],
    checked_at: str,
) -> object:
    if field == "run_id":
        return proof["command_run_id"]
    if field == "checked_at":
        return checked_at
    if field == "validation_timestamp":
        return "<validation-timestamp>"
    if field == "proof_outcome":
        return "<accepted-or-failed>"
    if field == "post_capture_validation_results":
        return {
            str(check): "<passed-or-failed>"
            for check in proof["post_capture_validation_checks"]
        }
    if field == "secret_redaction_check":
        return "<passed-after-no-secret-scan>"
    if field == "realtime_provider":
        return "openrouter_livekit"
    if field == "execute_live_calls":
        return "<true-after-live-call>"
    if field == "participant_identity":
        return "<participant-identity>"
    if field == "realtime_session_id_or_livekit_room":
        return "<livekit-room-or-realtime-session-id>"
    if field == "destination_channel":
        return "<destination-channel>"
    if field == "durable_platform_id_or_url":
        return "<durable-platform-id-or-url>"
    if field == "runtime_configuration_snapshot_id":
        return "<runtime-configuration-snapshot-id>"
    if field.endswith("_artifact_id") or field.endswith("_snapshot_id"):
        return "<artifact-id>"
    return f"<{proof_name}-{field}>"


def _provider_proof_record_validation_payload(
    args: argparse.Namespace,
    record: object,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    proof_plan = _provider_proof_plan_payload(args, env_values=env_values)
    proof_name = args.proof
    proofs = proof_plan["proofs"]
    if proof_name not in proofs:
        return {
            "artifact": "agent-studio-provider-proof-record-validation",
            "boundary": "no_secret_values_printed_no_state_change",
            "checked_at": proof_plan["checked_at"],
            "proof": proof_name,
            "status": "invalid_record",
            "state_change_allowed": False,
            "issue_codes": ["unknown_proof"],
            "issues": [
                {
                    "code": "unknown_proof",
                    "field": "proof",
                }
            ],
        }

    proof = proofs[proof_name]
    schema = proof["proof_artifact_schema"]
    product_run_id_state = proof["product_run_id_state"]
    required_fields = schema["required_fields"]
    allowed_outcomes = schema["allowed_outcomes"]
    issues: list[dict[str, object]] = []
    issue_codes: list[str] = []

    def add_issue(code: str, field: str, detail: str | None = None) -> None:
        issue = {"code": code, "field": field}
        if detail:
            issue["detail"] = detail
        issues.append(issue)
        if code not in issue_codes:
            issue_codes.append(code)

    if not isinstance(record, Mapping):
        add_issue("record_must_be_object", "$")
        for secret_path in _provider_proof_record_secret_paths(record):
            add_issue("token_shaped_value_detected", secret_path)
        return {
            "artifact": "agent-studio-provider-proof-record-validation",
            "boundary": "no_secret_values_printed_no_state_change",
            "checked_at": proof_plan["checked_at"],
            "proof": proof_name,
            "command_run_id": proof["command_run_id"],
            "run_id_state": proof["run_id_state"],
            "product_run_id_state": product_run_id_state,
            "proof_outcome": None,
            "proof_artifact_schema": schema,
            "status": "invalid_record",
            "state_change_allowed": False,
            "issue_codes": issue_codes,
            "issues": issues,
        }

    for field in required_fields:
        value = record.get(field)
        if field not in record or value is None or value == "":
            add_issue("missing_required_field", field)
        elif _provider_proof_record_template_placeholder(value):
            add_issue("template_placeholder_not_replaced", field)

    proof_outcome = record.get("proof_outcome")
    if proof_outcome not in allowed_outcomes:
        add_issue("invalid_outcome", "proof_outcome")

    if proof.get("run_id_state") != "concrete_run_id":
        add_issue(
            "run_id_not_concrete",
            "run_id",
            "proof records require a durable product run UUID before validation or recording",
        )
    elif product_run_id_state != "product_run_uuid":
        add_issue(
            "run_id_not_product_uuid",
            "run_id",
            (
                "proof records require a durable product run UUID before "
                "validation or recording"
            ),
        )
    elif record.get("run_id") != proof["command_run_id"]:
        add_issue("run_id_mismatch", "run_id")

    validation_timestamp = record.get("validation_timestamp")
    if (
        validation_timestamp is not None
        and not _provider_proof_record_template_placeholder(validation_timestamp)
        and (
            not isinstance(validation_timestamp, str)
            or _provider_proof_audit_validation_time(validation_timestamp) is None
        )
    ):
        add_issue("invalid_validation_timestamp", "validation_timestamp")

    validation_results = record.get("post_capture_validation_results")
    if isinstance(validation_results, Mapping):
        placeholder_results = [
            check
            for check, value in validation_results.items()
            if _provider_proof_record_template_placeholder(value)
        ]
        if placeholder_results:
            add_issue(
                "template_placeholder_not_replaced",
                "post_capture_validation_results",
                f"{len(placeholder_results)} template placeholder results remain",
            )
        if proof_outcome == "accepted":
            missing_checks = [
                check
                for check in proof["post_capture_validation_checks"]
                if validation_results.get(check) not in {True, "passed"}
            ]
            if missing_checks:
                add_issue(
                    "missing_validation_results",
                    "post_capture_validation_results",
                    f"{len(missing_checks)} checks missing or not passed",
                )
            if proof_name == "provider-backed-live-voice-proof":
                if record.get("voice_edge_benchmark_status") != "ready":
                    add_issue(
                        "voice_edge_benchmark_not_ready",
                        "voice_edge_benchmark_status",
                    )
                if record.get("execute_live_calls") is not True:
                    add_issue("execute_live_calls_not_true", "execute_live_calls")
                if record.get("realtime_provider") != "openrouter_livekit":
                    add_issue(
                        "realtime_provider_not_openrouter_livekit",
                        "realtime_provider",
                    )
            elif proof_name == "external-publication-proof":
                destination_channel = record.get("destination_channel")
                normalized_destination_channel = (
                    _provider_proof_normalized_publish_channel_platform(
                        destination_channel
                    )
                    if isinstance(destination_channel, str)
                    else ""
                )
                if normalized_destination_channel != "linkedin":
                    add_issue("destination_channel_not_linkedin", "destination_channel")
                if (
                    _provider_proof_publication_destination_platform(
                        record.get("durable_platform_id_or_url")
                    )
                    != "linkedin"
                ):
                    add_issue(
                        "durable_destination_not_linkedin",
                        "durable_platform_id_or_url",
                    )
                if _provider_proof_publication_destination_is_local_substitute(
                    record.get("durable_platform_id_or_url")
                ):
                    add_issue(
                        "durable_destination_not_external",
                        "durable_platform_id_or_url",
                    )
                elif not _provider_proof_publication_channel_matches_destination(
                    record.get("destination_channel"),
                    record.get("durable_platform_id_or_url"),
                ):
                    add_issue(
                        "destination_channel_mismatch",
                        "durable_platform_id_or_url",
                    )
        elif not validation_results:
            add_issue(
                "missing_validation_results",
                "post_capture_validation_results",
                "failed proof records must include at least one failed check",
            )
    else:
        add_issue(
            "missing_validation_results",
            "post_capture_validation_results",
        )

    if record.get("secret_redaction_check") not in {True, "passed"}:
        add_issue("secret_redaction_check_not_passed", "secret_redaction_check")

    for secret_path in _provider_proof_record_secret_paths(record):
        add_issue("token_shaped_value_detected", secret_path)

    preflight_validation_report = (
        _provider_proof_record_preflight_validation_report(
            args,
            proof_name=proof_name,
            proof=proof,
            record=record,
            proof_outcome=proof_outcome,
            add_issue=add_issue,
        )
    )
    workspace_validation_report = (
        _provider_proof_record_workspace_validation_report(
            args,
            proof_name=proof_name,
            proof=proof,
            record=record,
            proof_outcome=proof_outcome,
            add_issue=add_issue,
        )
    )

    status = "invalid_record"
    state_change_allowed = False
    if not issues:
        status = (
            "valid_accepted_record"
            if proof_outcome == "accepted"
            else "valid_failed_record"
        )
        state_change_allowed = proof_outcome == "accepted"

    return {
        "artifact": "agent-studio-provider-proof-record-validation",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": proof_plan["checked_at"],
        "proof": proof_name,
        "command_run_id": proof["command_run_id"],
        "run_id_state": proof["run_id_state"],
        "product_run_id_state": product_run_id_state,
        "proof_outcome": proof_outcome,
        "proof_artifact_schema": schema,
        "status": status,
        "state_change_allowed": state_change_allowed,
        "issue_codes": issue_codes,
        "issues": issues,
        **(
            {"preflight_validation_report": preflight_validation_report}
            if preflight_validation_report is not None
            else {}
        ),
        **(
            {"workspace_validation_report": workspace_validation_report}
            if workspace_validation_report is not None
            else {}
        ),
    }


def _provider_proof_record_preflight_validation_report(
    args: argparse.Namespace,
    *,
    proof_name: str,
    proof: Mapping[str, object],
    record: Mapping[str, object],
    proof_outcome: object,
    add_issue,
) -> dict[str, object] | None:
    report_path = getattr(args, "preflight_validation_path", None)
    if proof_outcome != "accepted":
        return None
    if report_path is None:
        report_reference = record.get("preflight_validation_report_artifact_id")
        if (
            not isinstance(report_reference, str)
            or not report_reference.strip()
            or _provider_proof_record_template_placeholder(report_reference)
        ):
            add_issue(
                "preflight_validation_report_required",
                "preflight_validation_report_artifact_id",
            )
            return {
                "status": "missing_preflight_validation_report",
                "path": "n/a",
                "matched_fields": [],
            }
        report_path = report_reference

    safe_report_path = _provider_proof_output_path_text(report_path)
    matched_fields: list[str] = []
    validated_channels: list[str] = []
    validated_runtime_checks: list[str] = []
    validated_product_run_id: str | None = None

    def summary(status: str) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": status,
            "path": safe_report_path,
            "matched_fields": matched_fields,
        }
        if validated_runtime_checks:
            payload["validated_runtime_checks"] = validated_runtime_checks
        if validated_channels:
            payload["validated_publish_channels"] = validated_channels
        if validated_product_run_id:
            payload["validated_product_run_id"] = validated_product_run_id
        return payload

    report_start_added = 0

    def add_report_issue(code: str, field: str, detail: str | None = None) -> None:
        nonlocal report_start_added
        add_issue(code, field, detail)
        report_start_added += 1

    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(str(report_path)):
        add_report_issue(
            "token_shaped_value_detected",
            "preflight_validation_path",
            "preflight validation report path contains token-shaped text",
        )
        return summary("invalid_preflight_report_linkage")

    report_reference = record.get("preflight_validation_report_artifact_id")
    if proof_outcome == "accepted" and report_reference != safe_report_path:
        add_report_issue(
            "preflight_validation_report_artifact_id_mismatch",
            "preflight_validation_report_artifact_id",
        )

    try:
        report_text = Path(report_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        add_report_issue("preflight_validation_report_missing", "preflight_validation_path")
        return summary("invalid_preflight_report_linkage")
    except OSError:
        add_report_issue(
            "preflight_validation_report_unreadable",
            "preflight_validation_path",
        )
        return summary("invalid_preflight_report_linkage")
    except UnicodeDecodeError:
        add_report_issue("preflight_validation_report_not_utf8", "preflight_validation_path")
        return summary("invalid_preflight_report_linkage")

    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(report_text):
        add_report_issue(
            "token_shaped_value_detected",
            "preflight_validation_report",
        )

    try:
        report = json.loads(report_text)
    except json.JSONDecodeError:
        add_report_issue(
            "preflight_validation_report_invalid_json",
            "preflight_validation_path",
        )
        return summary("invalid_preflight_report_linkage")

    if not isinstance(report, Mapping):
        add_report_issue(
            "preflight_validation_report_must_be_object",
            "preflight_validation_path",
        )
        return summary("invalid_preflight_report_linkage")

    for secret_path in _provider_proof_record_secret_paths(report):
        add_report_issue("token_shaped_value_detected", secret_path)

    if (
        report.get("artifact")
        != "agent-studio-provider-proof-preflight-artifacts-validation"
    ):
        add_report_issue(
            "preflight_validation_report_artifact_mismatch",
            "preflight_validation_path",
        )
    if report.get("proof") != proof_name:
        add_report_issue(
            "preflight_validation_report_proof_mismatch",
            "preflight_validation_path",
        )
    if report.get("command_run_id") != proof.get("command_run_id"):
        add_report_issue(
            "preflight_validation_report_run_id_mismatch",
            "preflight_validation_path",
        )
    if report.get("status") != "valid_preflight_artifacts":
        add_report_issue(
            "preflight_validation_report_not_valid",
            "preflight_validation_path",
        )
    if report.get("issue_codes"):
        add_report_issue(
            "preflight_validation_report_has_issues",
            "preflight_validation_path",
        )

    report_artifact_ids = report.get("preflight_artifact_ids")
    if not isinstance(report_artifact_ids, Mapping):
        add_report_issue(
            "preflight_validation_report_missing_artifact_ids",
            "preflight_validation_path",
        )
        return summary("invalid_preflight_report_linkage")

    for field in _proof_preflight_artifact_id_fields(proof_name):
        if record.get(field) == report_artifact_ids.get(field):
            matched_fields.append(field)
        else:
            add_report_issue("preflight_artifact_id_mismatch", field)

    raw_product_run_id = report.get("validated_product_run_id")
    if raw_product_run_id != proof.get("command_run_id"):
        add_report_issue(
            "preflight_validation_report_product_run_id_mismatch",
            "preflight_validation_path",
        )
    elif isinstance(raw_product_run_id, str):
        validated_product_run_id = raw_product_run_id

    if proof_name == "provider-backed-live-voice-proof":
        raw_checks = report.get("validated_runtime_checks")
        if not isinstance(raw_checks, list) or not raw_checks:
            add_report_issue(
                "preflight_validation_report_missing_runtime_checks",
                "preflight_validation_path",
            )
        else:
            parsed_runtime_checks: list[str] = []
            for check in raw_checks:
                if not isinstance(check, str):
                    add_report_issue(
                        "preflight_validation_report_invalid_runtime_checks",
                        "preflight_validation_path",
                    )
                    continue
                parsed_runtime_checks.append(check)
                if check in VOICE_PROOF_REQUIRED_RUNTIME_CHECKS:
                    validated_runtime_checks.append(check)
            if parsed_runtime_checks != list(VOICE_PROOF_REQUIRED_RUNTIME_CHECKS):
                add_report_issue(
                    "preflight_validation_report_runtime_checks_not_canonical",
                    "preflight_validation_path",
                )
            for check_id in VOICE_PROOF_REQUIRED_RUNTIME_CHECKS:
                if check_id not in validated_runtime_checks:
                    add_report_issue(
                        "runtime_check_missing_from_preflight",
                        "preflight_validation_path",
                    )

    if proof_name == "external-publication-proof":
        raw_channels = report.get("validated_publish_channels")
        if not isinstance(raw_channels, list) or not raw_channels:
            add_report_issue(
                "preflight_validation_report_missing_publish_channels",
                "preflight_validation_path",
            )
        else:
            raw_channel_strings: list[str] = []
            publish_channel_summary_entries_are_strings = True
            for channel in raw_channels:
                if not isinstance(channel, str):
                    add_report_issue(
                        "preflight_validation_report_invalid_publish_channels",
                        "preflight_validation_path",
                    )
                    publish_channel_summary_entries_are_strings = False
                    continue
                raw_channel_strings.append(channel)
            parsed_channels, publish_channel_summary_is_canonical = (
                _provider_proof_publish_channel_summary_entries(raw_channel_strings)
            )
            for platform in parsed_channels:
                if (
                    platform in PUBLISH_CHANNEL_CREDENTIAL_ENVS
                    and platform not in validated_channels
                ):
                    validated_channels.append(platform)
            if (
                not publish_channel_summary_entries_are_strings
                or not publish_channel_summary_is_canonical
            ):
                add_report_issue(
                    "preflight_validation_report_publish_channels_not_canonical",
                    "preflight_validation_path",
                )
            if not _provider_proof_external_publication_channels_are_linkedin_only(
                validated_channels
            ):
                add_report_issue(
                    "preflight_validation_report_publish_channels_not_linkedin_only",
                    "preflight_validation_path",
                )
            destination_channel = record.get("destination_channel")
            normalized_destination_channel = (
                _provider_proof_normalized_publish_channel_platform(
                    destination_channel
                )
                if isinstance(destination_channel, str)
                else ""
            )
            if normalized_destination_channel not in validated_channels:
                add_report_issue(
                    "destination_channel_missing_from_preflight",
                    "destination_channel",
                )

    if report_start_added:
        return summary("invalid_preflight_report_linkage")
    return summary("valid_preflight_artifacts")


def _provider_proof_record_workspace_validation_report(
    args: argparse.Namespace,
    *,
    proof_name: str,
    proof: Mapping[str, object],
    record: Mapping[str, object],
    proof_outcome: object,
    add_issue,
) -> dict[str, object] | None:
    report_path = getattr(args, "workspace_validation_path", None)
    if proof_outcome != "accepted":
        return None
    if report_path is None:
        report_reference = record.get("workspace_validation_report_artifact_id")
        if (
            not isinstance(report_reference, str)
            or not report_reference.strip()
            or _provider_proof_record_template_placeholder(report_reference)
        ):
            add_issue(
                "workspace_validation_report_required",
                "workspace_validation_report_artifact_id",
            )
            return {
                "status": "missing_workspace_validation_report",
                "path": "n/a",
                "matched_fields": [],
            }
        report_path = report_reference

    safe_report_path = _provider_proof_output_path_text(report_path)
    matched_fields: list[str] = []

    def summary(status: str) -> dict[str, object]:
        return {
            "status": status,
            "path": safe_report_path,
            "matched_fields": matched_fields,
        }

    report_issue_count = 0

    def add_report_issue(code: str, field: str, detail: str | None = None) -> None:
        nonlocal report_issue_count
        add_issue(code, field, detail)
        report_issue_count += 1

    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(str(report_path)):
        add_report_issue(
            "token_shaped_value_detected",
            "workspace_validation_path",
            "workspace validation report path contains token-shaped text",
        )
        return summary("invalid_workspace_validation_report_linkage")

    report_reference = record.get("workspace_validation_report_artifact_id")
    if proof_outcome == "accepted" and report_reference != safe_report_path:
        add_report_issue(
            "workspace_validation_report_artifact_id_mismatch",
            "workspace_validation_report_artifact_id",
        )

    try:
        report_text = Path(report_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        add_report_issue(
            "workspace_validation_report_missing",
            "workspace_validation_path",
        )
        return summary("invalid_workspace_validation_report_linkage")
    except OSError:
        add_report_issue(
            "workspace_validation_report_unreadable",
            "workspace_validation_path",
        )
        return summary("invalid_workspace_validation_report_linkage")
    except UnicodeDecodeError:
        add_report_issue(
            "workspace_validation_report_not_utf8",
            "workspace_validation_path",
        )
        return summary("invalid_workspace_validation_report_linkage")

    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(report_text):
        add_report_issue(
            "token_shaped_value_detected",
            "workspace_validation_report",
        )

    try:
        report = json.loads(report_text)
    except json.JSONDecodeError:
        add_report_issue(
            "workspace_validation_report_invalid_json",
            "workspace_validation_path",
        )
        return summary("invalid_workspace_validation_report_linkage")

    if not isinstance(report, Mapping):
        add_report_issue(
            "workspace_validation_report_must_be_object",
            "workspace_validation_path",
        )
        return summary("invalid_workspace_validation_report_linkage")

    for secret_path in _provider_proof_record_secret_paths(report):
        add_report_issue("token_shaped_value_detected", secret_path)

    if report.get("artifact") != "agent-studio-provider-proof-workspace-validation":
        add_report_issue(
            "workspace_validation_report_artifact_mismatch",
            "workspace_validation_path",
        )
    if report.get("run_id") != proof.get("command_run_id"):
        add_report_issue(
            "workspace_validation_report_run_id_mismatch",
            "workspace_validation_path",
        )
    if report.get("run_id_state") != "concrete_run_id":
        add_report_issue(
            "workspace_validation_report_run_id_not_concrete",
            "workspace_validation_path",
        )
    if report.get("status") != "valid_workspace":
        add_report_issue(
            "workspace_validation_report_not_valid",
            "workspace_validation_path",
        )
    if report.get("issue_codes"):
        add_report_issue(
            "workspace_validation_report_has_issues",
            "workspace_validation_path",
        )

    expected_files = report.get("expected_files")
    validated_files = report.get("validated_files")
    if not isinstance(expected_files, list) or not isinstance(validated_files, list):
        add_report_issue(
            "workspace_validation_report_missing_files",
            "workspace_validation_path",
        )
        return summary("invalid_workspace_validation_report_linkage")

    expected_names = {Path(str(path)).name for path in expected_files}
    validated_names = {Path(str(path)).name for path in validated_files}
    for file_name in (f"{proof_name}.template.json", "README.md"):
        if file_name not in expected_names:
            add_report_issue(
                "workspace_expected_file_missing",
                "workspace_validation_path",
                file_name,
            )
        elif file_name not in validated_names:
            add_report_issue(
                "workspace_validated_file_missing",
                "workspace_validation_path",
                file_name,
            )
        else:
            matched_fields.append(file_name)

    if report_issue_count:
        return summary("invalid_workspace_validation_report_linkage")
    return summary("valid_workspace")


VOICE_PROOF_REQUIRED_PREFLIGHT_FLAGS = (
    "preflight_livekit",
    "preflight_edge",
    "preflight_agent",
    "preflight_gemma",
    "preflight_tts",
)

VOICE_PROOF_REQUIRED_RUNTIME_CHECKS = (
    "livekit-transport",
    "livekit-agent-participant",
    "voice-agent-backend-event-sink",
    "openrouter-live-dialogue-reasoning",
    "kokoro-tts",
    "rust-voice-edge",
)

PUBLISH_PROOF_ALLOWED_PREFLIGHT_REVIEW_ISSUES = {
    "publish_channel_policy_review_required",
}

PRODUCT_RUN_PREFLIGHT_REQUIRED_FIELDS = (
    "run_id",
    "goal",
    "status",
    "conversation_state",
    "active_agents",
    "source_record_ids",
    "artifact_ids",
    "feedback_item_ids",
    "created_at",
    "updated_at",
)


def _status_value(value: object) -> object:
    return getattr(value, "value", value)


def _provider_proof_preflight_artifact_semantic_checks(
    *,
    proof_name: str,
    file_name: str,
    safe_path: str,
    parsed: Mapping[str, object],
    command_run_id: str,
    add_issue,
) -> None:
    if file_name == "product-run.preflight.json":
        _provider_proof_product_run_semantic_checks(
            safe_path=safe_path,
            parsed=parsed,
            command_run_id=command_run_id,
            add_issue=add_issue,
        )
        return
    if proof_name == "provider-backed-live-voice-proof":
        if file_name == "provider-readiness.preflight.json":
            _provider_proof_provider_readiness_semantic_checks(
                safe_path=safe_path,
                parsed=parsed,
                add_issue=add_issue,
            )
        elif file_name == "voice-runtime-readiness.preflight.json":
            _provider_proof_voice_runtime_semantic_checks(
                safe_path=safe_path,
                parsed=parsed,
                add_issue=add_issue,
            )
    elif (
        proof_name == "external-publication-proof"
        and file_name == "publish-readiness.preflight.json"
    ):
        _provider_proof_publish_readiness_semantic_checks(
            safe_path=safe_path,
            parsed=parsed,
            add_issue=add_issue,
        )


def _provider_proof_product_run_semantic_checks(
    *,
    safe_path: str,
    parsed: Mapping[str, object],
    command_run_id: str,
    add_issue,
) -> None:
    run_id = parsed.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        add_issue(
            "product_run_id_missing",
            safe_path,
            json_path="run_id",
        )
        return
    if run_id != command_run_id:
        add_issue(
            "product_run_id_mismatch",
            safe_path,
            json_path="run_id",
        )
        return
    missing_fields = [
        field
        for field in PRODUCT_RUN_PREFLIGHT_REQUIRED_FIELDS
        if field not in parsed
    ]
    if missing_fields:
        add_issue(
            "product_run_payload_schema_invalid",
            safe_path,
            "product-run preflight must be the /api/runs/<run-id> response shape",
            json_path=missing_fields[0],
        )
        return
    try:
        run = RunState.model_validate(parsed)
    except ValidationError:
        add_issue(
            "product_run_payload_schema_invalid",
            safe_path,
            "product-run preflight does not match the expected run response schema",
        )
        return
    if str(run.run_id) != command_run_id:
        add_issue(
            "product_run_id_mismatch",
            safe_path,
            json_path="run_id",
        )


def _provider_proof_provider_readiness_semantic_checks(
    *,
    safe_path: str,
    parsed: Mapping[str, object],
    add_issue,
) -> None:
    try:
        readiness = ProviderReadinessResult.model_validate(parsed)
    except ValidationError:
        add_issue(
            "preflight_payload_schema_invalid",
            safe_path,
            "provider-readiness payload does not match the expected schema",
        )
        return

    provider_by_id = {provider.provider_id: provider for provider in readiness.providers}
    openrouter_livekit = provider_by_id.get("openrouter-livekit")
    if readiness.default_realtime_provider != "openrouter_livekit":
        add_issue(
            "provider_readiness_realtime_provider_not_openrouter_livekit",
            safe_path,
        )
    if (
        openrouter_livekit is None
        or _status_value(openrouter_livekit.status) != "ready"
        or not openrouter_livekit.selected
        or "openrouter-livekit" not in readiness.ready_provider_ids
    ):
        add_issue(
            "provider_readiness_openrouter_livekit_not_ready",
            safe_path,
        )


def _provider_proof_voice_runtime_semantic_checks(
    *,
    safe_path: str,
    parsed: Mapping[str, object],
    add_issue,
) -> None:
    try:
        readiness = VoiceRuntimeReadinessResult.model_validate(parsed)
    except ValidationError:
        add_issue(
            "preflight_payload_schema_invalid",
            safe_path,
            "voice-runtime-readiness payload does not match the expected schema",
        )
        return

    if _status_value(readiness.status) != "ready":
        add_issue("voice_runtime_readiness_not_ready", safe_path)
    if readiness.selected_provider != "openrouter_livekit":
        add_issue("voice_runtime_selected_provider_not_openrouter_livekit", safe_path)
    for flag in VOICE_PROOF_REQUIRED_PREFLIGHT_FLAGS:
        if getattr(readiness, flag) is not True:
            add_issue(
                "voice_runtime_preflight_flag_missing",
                safe_path,
                json_path=flag,
            )

    check_by_id = {}
    seen_check_ids: set[str] = set()
    duplicate_check_ids: set[str] = set()
    for check in readiness.checks:
        if check.check_id in seen_check_ids:
            duplicate_check_ids.add(check.check_id)
        seen_check_ids.add(check.check_id)
        check_by_id[check.check_id] = check
    for check_id in sorted(duplicate_check_ids):
        add_issue(
            "voice_runtime_duplicate_check_id",
            safe_path,
            json_path="checks.check_id",
        )
    for check_id in VOICE_PROOF_REQUIRED_RUNTIME_CHECKS:
        check = check_by_id.get(check_id)
        if check is None or _status_value(check.status) != "ready":
            add_issue(
                "voice_runtime_required_check_not_ready",
                safe_path,
                json_path=f"checks.{check_id}",
            )


def _provider_proof_publish_readiness_semantic_checks(
    *,
    safe_path: str,
    parsed: Mapping[str, object],
    add_issue,
) -> None:
    try:
        readiness = PublishReadinessResult.model_validate(parsed)
    except ValidationError:
        add_issue(
            "preflight_payload_schema_invalid",
            safe_path,
            "publish-readiness payload does not match the expected schema",
        )
        return

    status = _status_value(readiness.status)
    if status == "ready":
        if readiness.ready is not True or readiness.blocking_issues:
            add_issue("publish_readiness_not_ready", safe_path)
    elif status == "needs_review":
        if (
            readiness.blocking_issues
            != ["publish_channel_policy_review_required"]
            or readiness.ready is not False
        ):
            add_issue("publish_readiness_not_ready", safe_path)
    else:
        add_issue("publish_readiness_not_ready", safe_path)

    if readiness.feedback_gate_opened:
        add_issue("publish_readiness_feedback_gate_opened", safe_path)
    if not readiness.publish_channel_checks:
        add_issue("publish_readiness_missing_channel_checks", safe_path)
    has_pending_policy_review = False
    seen_platforms: set[str] = set()
    for index, check in enumerate(readiness.publish_channel_checks):
        platform = _provider_proof_normalized_publish_channel_platform(
            check.platform
        )
        if not platform:
            add_issue(
                "publish_channel_platform_missing",
                safe_path,
                json_path=f"publish_channel_checks.{index}.platform",
            )
        elif platform not in PUBLISH_CHANNEL_CREDENTIAL_ENVS:
            add_issue(
                "publish_channel_platform_unsupported",
                safe_path,
                json_path=f"publish_channel_checks.{index}.platform",
            )
        elif platform in seen_platforms:
            add_issue(
                "publish_channel_duplicate_platform",
                safe_path,
                json_path=f"publish_channel_checks.{index}.platform",
            )
        else:
            seen_platforms.add(platform)
        if status == "ready" and check.blocking_issues:
            add_issue(
                "publish_channel_blocking_issues_present",
                safe_path,
                json_path=f"publish_channel_checks.{index}.blocking_issues",
            )
        elif status == "needs_review" and tuple(check.blocking_issues) not in {
            (),
            ("publish_channel_policy_review_required",),
        }:
            add_issue(
                "publish_channel_blocking_issues_not_policy_review",
                safe_path,
                json_path=f"publish_channel_checks.{index}.blocking_issues",
            )
        if (
            status == "needs_review"
            and check.policy_status == "acknowledged"
            and check.blocking_issues
        ):
            add_issue(
                "publish_channel_policy_blocker_already_acknowledged",
                safe_path,
                json_path=f"publish_channel_checks.{index}.blocking_issues",
            )
        if check.credential_status != "configured":
            add_issue(
                "publish_channel_credentials_not_configured",
                safe_path,
                json_path=f"publish_channel_checks.{index}.credential_status",
            )
        allowed_policy_statuses = (
            {"acknowledged"}
            if status == "ready"
            else {"needs_review", "acknowledged"}
        )
        if check.policy_status not in allowed_policy_statuses:
            add_issue(
                "publish_channel_policy_not_reviewed",
                safe_path,
                json_path=f"publish_channel_checks.{index}.policy_status",
            )
        if check.policy_status == "needs_review":
            has_pending_policy_review = True
    if status == "needs_review" and not has_pending_policy_review:
        add_issue(
            "publish_channel_policy_review_not_pending",
            safe_path,
        )


def _provider_proof_preflight_artifacts_validation_payload(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    proof_plan = _provider_proof_plan_payload(args, env_values=env_values)
    proof_name = args.proof
    proofs = proof_plan["proofs"]
    if proof_name not in proofs:
        return {
            "artifact": "agent-studio-provider-proof-preflight-artifacts-validation",
            "boundary": "no_secret_values_printed_no_state_change",
            "checked_at": proof_plan["checked_at"],
            "proof": proof_name,
            "status": "invalid_preflight_artifacts",
            "state_change_allowed": False,
            "issue_codes": ["unknown_proof"],
            "issues": [{"code": "unknown_proof", "field": "proof"}],
            "expected_files": [],
            "validated_files": [],
            "preflight_artifact_ids": {},
        }

    proof = proofs[proof_name]
    preflight_dir = args.preflight_dir
    safe_preflight_dir = _provider_proof_portable_path_text(preflight_dir)
    raw_expected_files = _proof_preflight_output_files_for_output(
        proof_name,
        preflight_dir,
    )
    expected_files = [
        _provider_proof_portable_path_text(path) for path in raw_expected_files
    ]
    issues: list[dict[str, object]] = []
    issue_codes: list[str] = []
    validated_files: list[str] = []
    validated_publish_channels: list[str] = []
    validated_runtime_checks: list[str] = []
    validated_product_run_id: str | None = None

    def add_issue(
        code: str,
        field: str,
        detail: str | None = None,
        json_path: str | None = None,
    ) -> None:
        issue: dict[str, object] = {"code": code, "field": field}
        if detail:
            issue["detail"] = detail
        if json_path:
            issue["json_path"] = json_path
        issues.append(issue)
        if code not in issue_codes:
            issue_codes.append(code)

    if proof["run_id_state"] != "concrete_run_id":
        add_issue(
            "run_id_not_concrete",
            "run_id",
            "preflight artifact validation requires a durable product run UUID",
        )
    elif proof["product_run_id_state"] != "product_run_uuid":
        add_issue(
            "run_id_not_product_uuid",
            "run_id",
            (
                "preflight artifact validation requires a durable product run "
                "UUID"
            ),
        )

    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(str(preflight_dir)):
        add_issue(
            "token_shaped_value_detected",
            "preflight_dir",
            "preflight_dir contains token-shaped text",
        )

    for raw_path, safe_path in zip(raw_expected_files, expected_files, strict=True):
        path = Path(raw_path)
        file_issue_count = len(issues)
        if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(str(raw_path)):
            continue
        if not path.exists():
            add_issue("preflight_file_missing", safe_path)
            continue
        if not path.is_file():
            add_issue("preflight_path_not_file", safe_path)
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            add_issue("preflight_file_unreadable", safe_path)
            continue
        except UnicodeDecodeError:
            add_issue("preflight_file_not_utf8", safe_path)
            continue
        if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(content):
            add_issue("token_shaped_value_detected", safe_path)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            add_issue("preflight_file_invalid_json", safe_path)
            continue
        if not isinstance(parsed, Mapping):
            add_issue("preflight_file_must_be_object", safe_path)
        for secret_path in _provider_proof_record_secret_paths(parsed):
            add_issue(
                "token_shaped_value_detected",
                safe_path,
                json_path=secret_path,
            )
        if isinstance(parsed, Mapping):
            _provider_proof_preflight_artifact_semantic_checks(
                proof_name=proof_name,
                file_name=path.name,
                safe_path=safe_path,
                parsed=parsed,
                command_run_id=str(proof["command_run_id"]),
                add_issue=add_issue,
            )
            if path.name == "product-run.preflight.json":
                parsed_run_id = parsed.get("run_id")
                if parsed_run_id == proof["command_run_id"]:
                    validated_product_run_id = str(parsed_run_id)
            if (
                proof_name == "provider-backed-live-voice-proof"
                and path.name == "voice-runtime-readiness.preflight.json"
            ):
                validated_runtime_checks = (
                    _provider_proof_runtime_checks_from_preflight(parsed)
                )
            if (
                proof_name == "external-publication-proof"
                and path.name == "publish-readiness.preflight.json"
            ):
                validated_publish_channels = (
                    _provider_proof_publish_channels_from_preflight(parsed)
                )
        if len(issues) == file_issue_count:
            validated_files.append(safe_path)

    preflight_artifact_ids: dict[str, str] = {}
    status = "invalid_preflight_artifacts"
    if not issues:
        status = "valid_preflight_artifacts"
        preflight_artifact_ids = {
            field: _provider_proof_portable_path_text(path)
            for field, path in _proof_preflight_artifact_ids_for_output(
                proof_name,
                preflight_dir,
            ).items()
        }

    payload: dict[str, object] = {
        "artifact": "agent-studio-provider-proof-preflight-artifacts-validation",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": proof_plan["checked_at"],
        "proof": proof_name,
        "command_run_id": proof["command_run_id"],
        "run_id_state": proof["run_id_state"],
        "product_run_id_state": proof["product_run_id_state"],
        "preflight_dir": safe_preflight_dir,
        "expected_files": expected_files,
        "validated_files": validated_files,
        "preflight_artifact_ids": preflight_artifact_ids,
        "status": status,
        "state_change_allowed": False,
        "issue_codes": issue_codes,
        "issues": issues,
    }
    if proof_name == "external-publication-proof" and status == "valid_preflight_artifacts":
        payload["validated_publish_channels"] = validated_publish_channels
    if proof_name == "provider-backed-live-voice-proof" and status == "valid_preflight_artifacts":
        payload["validated_runtime_checks"] = validated_runtime_checks
    if status == "valid_preflight_artifacts" and validated_product_run_id:
        payload["validated_product_run_id"] = validated_product_run_id
    return payload


def _provider_proof_record_template_placeholder(value: object) -> bool:
    return (
        isinstance(value, str)
        and PROVIDER_PROOF_TEMPLATE_PLACEHOLDER_PATTERN.fullmatch(value.strip())
        is not None
    )


def _provider_proof_publication_destination_is_local_substitute(value: object) -> bool:
    if not isinstance(value, str):
        return True
    destination = value.strip()
    if not destination:
        return True
    lowered = destination.lower()
    if re.match(r"^[a-z]:[\\/]", lowered):
        return True
    if "\\" in destination:
        return True
    if lowered.startswith(("~", "/", "./", "../")):
        return True
    if lowered.startswith(("file:", "data:", "about:", "blob:")):
        return True
    parsed = urlparse(destination)
    if parsed.scheme and parsed.scheme not in {"http", "https", "ws", "wss"}:
        return not lowered.startswith("urn:li:share:")
    if not parsed.scheme:
        if "/" in destination:
            return True
        return (
            re.search(
                r"(^|[^a-z0-9])(draft|preview|local|internal)([^a-z0-9]|$)",
                lowered,
            )
            is not None
        )
    host = (parsed.hostname or "").lower()
    if parsed.scheme in {"http", "https", "ws", "wss"}:
        if (
            host == "localhost"
            or host == "::1"
            or host.endswith(".localhost")
            or host.endswith(".local")
        ):
            return True
        if "." not in host:
            return True
        if host.endswith(
            (".internal", ".lan", ".test", ".invalid", ".example")
        ):
            return True
        try:
            if not ipaddress.ip_address(host).is_global:
                return True
        except ValueError:
            pass
        path_segments = [
            segment
            for segment in parsed.path.lower().split("/")
            if segment
        ]
        if path_segments and path_segments[0] in {"draft", "preview"}:
            return True
        return False
    return False


def _provider_proof_openrouter_livekit_url_is_placeholder(value: object) -> bool:
    if not isinstance(value, str):
        return True
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").lower()
    if not host:
        return True
    return host.endswith((".example", ".invalid", ".test"))


def _provider_proof_publication_destination_platform(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    destination = value.strip().lower()
    if destination.startswith("urn:li:share:"):
        return "linkedin"
    parsed = urlparse(destination)
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        return "linkedin"
    if host == "instagram.com" or host.endswith(".instagram.com"):
        return "instagram"
    if host in {"x.com", "twitter.com"} or host.endswith(
        (".x.com", ".twitter.com")
    ):
        return "x"
    if host == "substack.com" or host.endswith(".substack.com"):
        return "substack"
    return None


def _provider_proof_publication_channel_matches_destination(
    channel: object,
    destination: object,
) -> bool:
    if not isinstance(channel, str):
        return False
    normalized_channel = channel.strip().lower()
    if normalized_channel in {"instagram_post", "instagram_reel"}:
        normalized_channel = "instagram"
    elif normalized_channel in {"twitter", "x_thread"}:
        normalized_channel = "x"
    platform = _provider_proof_publication_destination_platform(destination)
    return platform is None or platform == normalized_channel


def _record_provider_proof_record_payload(
    args: argparse.Namespace,
    record: object,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    validation = _provider_proof_record_validation_payload(
        args,
        record,
        env_values=env_values,
    )
    valid_statuses = {"valid_accepted_record", "valid_failed_record"}
    if validation["status"] not in valid_statuses:
        return {
            "artifact": "agent-studio-provider-proof-record-audit",
            "boundary": "no_secret_values_printed_no_state_change",
            "checked_at": validation["checked_at"],
            "proof": validation["proof"],
            "command_run_id": validation["command_run_id"],
            "proof_outcome": validation["proof_outcome"],
            "status": validation["status"],
            "validation_status": validation["status"],
            "validation_issue_codes": validation["issue_codes"],
            "audit_recorded": False,
            "state_change_allowed": False,
            "written_targets": [],
        }

    if not isinstance(record, Mapping):
        raise TypeError("valid provider proof record must be a mapping")

    targets = _provider_proof_record_audit_targets(args)
    audit_issues, audit_issue_codes = _provider_proof_audit_target_issues(targets)
    if audit_issues:
        return {
            "artifact": "agent-studio-provider-proof-record-audit",
            "boundary": "no_secret_values_printed_no_state_change",
            "checked_at": validation["checked_at"],
            "proof": validation["proof"],
            "command_run_id": validation["command_run_id"],
            "proof_outcome": validation["proof_outcome"],
            "status": "audit_target_unwritable",
            "validation_status": validation["status"],
            "validation_issue_codes": validation["issue_codes"],
            "audit_issue_codes": audit_issue_codes,
            "audit_issues": audit_issues,
            "audit_recorded": False,
            "state_change_allowed": False,
            "written_targets": [],
        }
    note = _provider_proof_record_audit_note(validation, record)
    for target in targets:
        _append_provider_proof_record_audit_note(target, note)

    return {
        "artifact": "agent-studio-provider-proof-record-audit",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": validation["checked_at"],
        "proof": validation["proof"],
        "command_run_id": validation["command_run_id"],
        "proof_outcome": validation["proof_outcome"],
        "status": "audit_recorded",
        "validation_status": validation["status"],
        "validation_issue_codes": validation["issue_codes"],
        "audit_recorded": True,
        "state_change_allowed": validation["state_change_allowed"],
        "written_targets": [
            _provider_proof_portable_path_text(target) for target in targets
        ],
    }


def _record_provider_proof_closure_review_payload(
    args: argparse.Namespace,
    record: object,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    validation = _provider_proof_closure_review_validation_payload(
        argparse.Namespace(
            env_example_path=args.env_example_path,
            checked_at=args.checked_at,
            run_id=args.run_id,
            audit_target=getattr(args, "proof_audit_target", None),
        ),
        record,
        env_values=env_values,
    )
    valid_statuses = {
        "valid_approved_closure_review",
        "valid_rejected_closure_review",
    }
    if validation["status"] not in valid_statuses:
        return {
            "artifact": "agent-studio-provider-proof-closure-review-audit",
            "boundary": "no_secret_values_printed_no_state_change",
            "checked_at": validation["checked_at"],
            "run_id": validation["run_id"],
            "status": validation["status"],
            "validation_status": validation["status"],
            "validation_issue_codes": validation["issue_codes"],
            "audit_recorded": False,
            "state_change_allowed": False,
            "blocker_state_update_allowed_after_review": False,
            "written_targets": [],
        }

    if not isinstance(record, Mapping):
        raise TypeError("valid provider proof closure review must be a mapping")

    targets = _provider_proof_record_audit_targets(args)
    audit_issues, audit_issue_codes = _provider_proof_audit_target_issues(targets)
    if audit_issues:
        return {
            "artifact": "agent-studio-provider-proof-closure-review-audit",
            "boundary": "no_secret_values_printed_no_state_change",
            "checked_at": validation["checked_at"],
            "run_id": validation["run_id"],
            "status": "audit_target_unwritable",
            "validation_status": validation["status"],
            "validation_issue_codes": validation["issue_codes"],
            "audit_issue_codes": audit_issue_codes,
            "audit_issues": audit_issues,
            "audit_recorded": False,
            "state_change_allowed": False,
            "blocker_state_update_allowed_after_review": False,
            "written_targets": [],
        }
    note = _provider_proof_closure_review_audit_note(validation, record)
    for target in targets:
        _append_provider_proof_record_audit_note(target, note)

    return {
        "artifact": "agent-studio-provider-proof-closure-review-audit",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": validation["checked_at"],
        "run_id": validation["run_id"],
        "status": "audit_recorded",
        "validation_status": validation["status"],
        "validation_issue_codes": validation["issue_codes"],
        "audit_recorded": True,
        "state_change_allowed": validation["state_change_allowed"],
        "blocker_state_update_allowed_after_review": validation[
            "blocker_state_update_allowed_after_review"
        ],
        "written_targets": [
            _provider_proof_portable_path_text(target) for target in targets
        ],
    }


def _provider_proof_completion_status_payload(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    proof_plan = _provider_proof_plan_payload(args, env_values=env_values)
    first_proof = next(iter(proof_plan["proofs"].values()))
    run_id_state = str(first_proof["run_id_state"])
    product_run_id_state = str(first_proof["product_run_id_state"])
    command_run_id = _proof_product_run_id_command_value(
        args.run_id,
        product_run_id_state=product_run_id_state,
    )
    targets = _provider_proof_record_audit_targets(args)
    target_paths = [_provider_proof_portable_path_text(target) for target in targets]
    audit_target_overrides = [
        _provider_proof_output_path_text(target)
        for target in (getattr(args, "audit_target", None) or [])
    ]
    proof_names = list(proof_plan["proofs"])
    base_payload = {
        "artifact": "agent-studio-provider-proof-completion-status",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": proof_plan["checked_at"],
        "run_id": command_run_id,
        "run_id_state": run_id_state,
        "product_run_id_state": product_run_id_state,
        "audit_targets": target_paths,
        "required_proofs": proof_names,
        "completion_requirements": [
            "run_id is a durable product UUID",
            "each required proof has a latest accepted record",
            "accepted records are present in every configured readable audit target",
            "no configured audit target is missing or invalid",
            "completion status command changes no blocker state",
        ],
        "state_change_boundary": {
            "command_changes_blocker_state": False,
            "status_only": True,
            "state_change_requires_external_update_after_review": True,
        },
        "blocker_state_change_allowed_by_this_command": False,
    }
    if run_id_state != "concrete_run_id" or product_run_id_state != "product_run_uuid":
        issue_code = (
            "run_id_not_concrete"
            if run_id_state != "concrete_run_id"
            else "run_id_not_product_uuid"
        )
        issue_detail = (
            "accepted proof completion status requires a durable product run UUID"
            if issue_code == "run_id_not_concrete"
            else (
                "accepted proof completion status requires a durable product "
                "run UUID"
            )
        )
        return {
            **base_payload,
            "status": "blocked_by_run_id",
            "issue_codes": [issue_code],
            "issues": [
                {
                    "code": issue_code,
                    "field": "run_id",
                    "detail": issue_detail,
                }
            ],
            "all_required_proofs_accepted": False,
            "accepted_proofs": [],
            "missing_accepted_proofs": proof_names,
            "missing_audit_targets": [],
            "invalid_audit_targets": [],
            "incomplete_audit_target_proofs": [],
            "latest_failed_proofs": [],
            "secret_shaped_audit_note_proofs": [],
            "invalid_accepted_audit_note_proofs": [],
            "proofs": {
                proof_name: {
                    **_provider_proof_completion_proof_payload(
                        proof_name,
                        command_run_id,
                        [],
                        [],
                        [],
                        [],
                        [],
                        proof_plan["proofs"][proof_name],
                        status_override="blocked_by_run_id",
                    ),
                    "accepted_record_found": False,
                    "source_targets": [],
                    "missing_source_targets": [],
                    "failed_source_targets": [],
                    "secret_source_targets": [],
                    "invalid_source_targets": [],
                }
                for proof_name in proof_names
            },
        }

    missing_targets: list[str] = []
    invalid_targets: list[str] = []
    readable_targets: list[str] = []
    accepted_sources: dict[str, list[str]] = {
        proof_name: [] for proof_name in proof_names
    }
    failed_sources: dict[str, list[str]] = {
        proof_name: [] for proof_name in proof_names
    }
    secret_sources: dict[str, list[str]] = {
        proof_name: [] for proof_name in proof_names
    }
    invalid_sources: dict[str, list[str]] = {
        proof_name: [] for proof_name in proof_names
    }
    for target in targets:
        target_text = _provider_proof_portable_path_text(target)
        if not target.exists():
            missing_targets.append(target_text)
            continue
        if not target.is_file():
            invalid_targets.append(target_text)
            continue
        try:
            body = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            invalid_targets.append(target_text)
            continue
        readable_targets.append(target_text)
        for proof_name in proof_names:
            proof = proof_plan["proofs"][proof_name]
            schema = proof["proof_artifact_schema"]
            if not isinstance(schema, Mapping):
                raise TypeError("proof_artifact_schema must be a mapping")
            required_audit_fields = _provider_proof_required_audit_note_fields(schema)
            validation_checks = proof["post_capture_validation_checks"]
            if not isinstance(validation_checks, list):
                raise TypeError("post_capture_validation_checks must be a list")
            latest_status = _provider_proof_latest_audit_record_status(
                body,
                proof_name=proof_name,
                run_id=command_run_id,
                expected_artifact_type=str(schema.get("artifact_type")),
                required_audit_fields=required_audit_fields,
                expected_validation_check_count=len(validation_checks),
            )
            if latest_status == "accepted":
                accepted_sources[proof_name].append(target_text)
            elif latest_status == "failed":
                failed_sources[proof_name].append(target_text)
            elif latest_status == "secret_shape_detected":
                secret_sources[proof_name].append(target_text)
            elif latest_status == "invalid_fields_detected":
                invalid_sources[proof_name].append(target_text)

    accepted_proofs = [
        proof_name
        for proof_name, sources in accepted_sources.items()
        if (
            sources
            and not failed_sources[proof_name]
            and not secret_sources[proof_name]
            and not invalid_sources[proof_name]
        )
    ]
    missing_proofs = [
        proof_name
        for proof_name, sources in accepted_sources.items()
        if (
            not sources
            and not failed_sources[proof_name]
            and not secret_sources[proof_name]
            and not invalid_sources[proof_name]
        )
    ]
    failed_proofs = [
        proof_name for proof_name, sources in failed_sources.items() if sources
    ]
    secret_proofs = [
        proof_name for proof_name, sources in secret_sources.items() if sources
    ]
    invalid_proofs = [
        proof_name for proof_name, sources in invalid_sources.items() if sources
    ]
    missing_sources_by_proof = {
        proof_name: [
            target
            for target in readable_targets
            if target not in accepted_sources[proof_name]
            and target not in failed_sources[proof_name]
            and target not in secret_sources[proof_name]
            and target not in invalid_sources[proof_name]
        ]
        for proof_name in proof_names
    }
    incomplete_proofs = [
        proof_name
        for proof_name, missing_sources in missing_sources_by_proof.items()
        if accepted_sources[proof_name] and missing_sources
    ]
    issue_codes: list[str] = []
    issues: list[dict[str, str]] = []
    if missing_proofs:
        issue_codes.append("accepted_proof_record_missing")
        issues.append(
            {
                "code": "accepted_proof_record_missing",
                "field": "audit_targets",
                "detail": (
                    "one or more required provider proof records has no accepted "
                    "audit note for this run id"
                ),
            }
        )
    if failed_proofs:
        issue_codes.append("latest_proof_record_failed")
        issues.append(
            {
                "code": "latest_proof_record_failed",
                "field": "audit_targets",
                "detail": (
                    "one or more required provider proof records has a latest "
                    "failed audit note for this run id"
                ),
            }
        )
    if secret_proofs:
        issue_codes.append("audit_note_secret_shape_detected")
        issues.append(
            {
                "code": "audit_note_secret_shape_detected",
                "field": "audit_targets",
                "detail": (
                    "one or more required provider proof audit notes contains "
                    "a token-shaped value"
                ),
            }
        )
    if invalid_proofs:
        issue_codes.append("accepted_audit_note_invalid_fields")
        issues.append(
            {
                "code": "accepted_audit_note_invalid_fields",
                "field": "audit_targets",
                "detail": (
                    "one or more accepted provider proof audit notes has fields "
                    "that contradict accepted proof requirements"
                ),
            }
        )
    if missing_targets:
        issue_codes.append("audit_targets_missing")
        issues.append(
            {
                "code": "audit_targets_missing",
                "field": "audit_targets",
                "detail": "one or more configured audit target files does not exist",
            }
        )
    if invalid_targets:
        issue_codes.append("audit_targets_invalid")
        issues.append(
            {
                "code": "audit_targets_invalid",
                "field": "audit_targets",
                "detail": "one or more configured audit targets is not a readable file",
            }
        )
    if incomplete_proofs:
        issue_codes.append("audit_target_coverage_incomplete")
        issues.append(
            {
                "code": "audit_target_coverage_incomplete",
                "field": "audit_targets",
                "detail": (
                    "one or more accepted provider proof records is missing "
                    "from a configured readable audit target"
                ),
            }
        )

    if secret_proofs:
        status = "blocked_by_secret_shaped_audit_note"
    elif invalid_proofs:
        status = "blocked_by_invalid_accepted_audit_note"
    elif missing_proofs:
        status = "blocked_by_missing_accepted_proof"
    elif failed_proofs:
        status = "blocked_by_latest_failed_proof_record"
    elif incomplete_proofs:
        status = "blocked_by_incomplete_audit_target_coverage"
    elif invalid_targets:
        status = "blocked_by_invalid_audit_target"
    elif missing_targets:
        status = "blocked_by_missing_audit_target"
    else:
        status = "required_proofs_accepted"

    output_dir_arg = getattr(args, "output_dir", None)
    output_dir = output_dir_arg
    if output_dir is None:
        output_dir = Path(
            f"social_media_optimiser/output/provider-proof/{command_run_id}"
        )
    completion_status_output_dir = output_dir_arg
    next_action = _provider_proof_completion_status_next_action(status)
    proof_payloads = {
        proof_name: {
            **_provider_proof_completion_proof_payload(
                proof_name,
                str(proof_plan["proofs"][proof_name]["command_run_id"]),
                accepted_sources[proof_name],
                failed_sources[proof_name],
                secret_sources[proof_name],
                invalid_sources[proof_name],
                missing_sources_by_proof[proof_name],
                proof_plan["proofs"][proof_name],
                output_dir=output_dir,
                completion_status_output_dir=completion_status_output_dir,
            ),
            "accepted_record_found": bool(accepted_sources[proof_name]),
            "source_targets": accepted_sources[proof_name],
            "missing_source_targets": missing_sources_by_proof[proof_name],
            "failed_source_targets": failed_sources[proof_name],
            "secret_source_targets": secret_sources[proof_name],
            "invalid_source_targets": invalid_sources[proof_name],
        }
        for proof_name in proof_names
    }
    next_action_commands: list[str] = []
    if next_action == "prepare_blocker_closure_review":
        next_action_commands = _proof_closure_review_template_commands(
            command_run_id,
            audit_target_overrides,
        )
    elif next_action == "capture_validate_record_and_recheck":
        next_action_commands = _provider_proof_completion_recovery_commands(
            proof_payloads,
            command_run_id,
            output_dir,
            completion_status_output_dir=completion_status_output_dir,
        )
    return {
        **base_payload,
        "status": status,
        "next_action": next_action,
        "next_action_commands": next_action_commands,
        "closure_review_packet": _provider_proof_closure_review_packet(
            run_id=command_run_id,
            proof_names=proof_names,
            accepted_sources=accepted_sources,
            ready_for_review=status == "required_proofs_accepted",
            audit_target_overrides=audit_target_overrides,
        ),
        "issue_codes": issue_codes,
        "issues": issues,
        "all_required_proofs_accepted": (
            not missing_proofs
            and not failed_proofs
            and not secret_proofs
            and not invalid_proofs
            and not incomplete_proofs
            and not missing_targets
            and not invalid_targets
        ),
        "accepted_proofs": accepted_proofs,
        "missing_accepted_proofs": missing_proofs,
        "missing_audit_targets": missing_targets,
        "invalid_audit_targets": invalid_targets,
        "incomplete_audit_target_proofs": incomplete_proofs,
        "latest_failed_proofs": failed_proofs,
        "secret_shaped_audit_note_proofs": secret_proofs,
        "invalid_accepted_audit_note_proofs": invalid_proofs,
        "proofs": proof_payloads,
    }


def _provider_proof_completion_status_next_action(status: str) -> str:
    if status == "required_proofs_accepted":
        return "prepare_blocker_closure_review"
    if status == "blocked_by_run_id":
        return "replace_run_id_and_recheck"
    return "capture_validate_record_and_recheck"


def _provider_proof_completion_recovery_commands(
    proof_payloads: Mapping[str, Mapping[str, object]],
    command_run_id: str,
    output_dir: Path,
    *,
    completion_status_output_dir: Path | None = None,
) -> list[str]:
    commands: list[str] = []
    for proof_name, proof_payload in proof_payloads.items():
        if proof_payload.get("next_action") != "capture_validate_record_and_recheck":
            continue
        if proof_payload.get("status") == "latest_record_failed":
            gate_commands = _provider_proof_operator_input_gate_commands_for_proof(
                proof_name,
                command_run_id,
                output_dir,
            )
            commands.extend(
                gate_commands
                or _provider_proof_capture_commands_after_unblock(
                    proof_name,
                    command_run_id,
                    output_dir,
                )
            )
            continue
        raw_commands = proof_payload.get("next_action_commands")
        if not isinstance(raw_commands, list):
            continue
        for command in raw_commands:
            if not isinstance(command, str):
                continue
            if " provider-proof-completion-status " in command:
                continue
            commands.append(command)
    if commands:
        commands.extend(
            _proof_completion_status_commands(
                command_run_id,
                output_dir=completion_status_output_dir,
            )
        )
    return commands


def _provider_proof_closure_review_packet(
    *,
    run_id: str,
    proof_names: list[str],
    accepted_sources: Mapping[str, list[str]],
    ready_for_review: bool,
    audit_target_overrides: list[str] | None = None,
) -> dict[str, object]:
    return {
        "ready_for_review": ready_for_review,
        "run_id": run_id,
        "review_required_before_state_change": True,
        "state_change_allowed_by_this_command": False,
        "required_proofs": proof_names,
        "accepted_record_sources": {
            proof_name: accepted_sources.get(proof_name, [])
            for proof_name in proof_names
        },
        "template_commands": _proof_closure_review_template_commands(
            run_id,
            audit_target_overrides,
        ),
        "state_update_candidates_after_review": [
            {
                "blocker": proof_name,
                "required_completion_status": "accepted_record_found",
                "candidate_state": "provider_proof_recorded_after_review",
            }
            for proof_name in proof_names
        ],
        "review_requirements": [
            "confirm every required proof has accepted_record_found status",
            (
                "confirm accepted proof records are present in every configured "
                "readable audit target"
            ),
            (
                "confirm accepted proof records preserve required schema, "
                "validation summary, and redaction proof"
            ),
            (
                "confirm no token-shaped values or secret material are present "
                "in audit notes"
            ),
            (
                "confirm blocker-state notes are updated only after reviewer "
                "approval"
            ),
        ],
    }


def _provider_proof_closure_review_template_payload(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    completion_status = _provider_proof_completion_status_payload(
        args,
        env_values=env_values,
    )
    base_payload = {
        "artifact": "agent-studio-provider-proof-closure-review-template",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": completion_status["checked_at"],
        "run_id": completion_status["run_id"],
        "run_id_state": completion_status["run_id_state"],
        "completion_status": completion_status["status"],
        "completion_issue_codes": completion_status["issue_codes"],
        "state_change_allowed": False,
        "next_commands": [],
    }
    if completion_status["status"] != "required_proofs_accepted":
        return {
            **base_payload,
            "status": "blocked_by_completion_status",
            "issue_codes": ["completion_status_not_accepted"],
            "issues": [
                {
                    "code": "completion_status_not_accepted",
                    "field": "completion_status",
                    "detail": (
                        "closure review template requires provider proof "
                        "completion status to be required_proofs_accepted"
                    ),
                }
            ],
            "template": None,
        }

    packet = completion_status["closure_review_packet"]
    if not isinstance(packet, Mapping):
        raise TypeError("closure_review_packet must be a mapping")
    review_requirements = packet.get("review_requirements")
    if not isinstance(review_requirements, list):
        raise TypeError("review_requirements must be a list")

    return {
        **base_payload,
        "status": "template_ready",
        "issue_codes": [],
        "issues": [],
        "next_commands": [
            *_proof_closure_review_validation_commands(
                str(completion_status["run_id"]),
                [
                    str(target)
                    for target in (getattr(args, "audit_target", None) or [])
                ],
            ),
            *_proof_closure_review_record_commands(
                str(completion_status["run_id"]),
                [
                    str(target)
                    for target in (getattr(args, "audit_target", None) or [])
                ],
            ),
        ],
        "template": {
            "run_id": completion_status["run_id"],
            "review_timestamp": "<review-timestamp>",
            "reviewer": "<reviewer-or-agent-id>",
            "review_decision": "<approved-or-rejected>",
            "completion_status": "required_proofs_accepted",
            "accepted_proofs": completion_status["accepted_proofs"],
            "accepted_record_sources": packet["accepted_record_sources"],
            "review_requirements": {
                str(requirement): "<confirmed-or-rejected>"
                for requirement in review_requirements
            },
            "state_update_candidates_after_review": packet[
                "state_update_candidates_after_review"
            ],
            "secret_redaction_check": "<passed-after-review>",
            "review_notes": "<no-secret-review-notes>",
        },
    }


def _print_provider_proof_closure_review_template(args: argparse.Namespace) -> None:
    payload = _provider_proof_closure_review_template_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _provider_proof_closure_review_validation_payload(
    args: argparse.Namespace,
    record: object,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    completion_status = _provider_proof_completion_status_payload(
        args,
        env_values=env_values,
    )
    base_payload = {
        "artifact": "agent-studio-provider-proof-closure-review-validation",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": completion_status["checked_at"],
        "run_id": completion_status["run_id"],
        "run_id_state": completion_status["run_id_state"],
        "completion_status": completion_status["status"],
        "state_change_allowed": False,
    }
    issues: list[dict[str, object]] = []
    issue_codes: list[str] = []

    def add_issue(code: str, field: str, detail: str | None = None) -> None:
        issue = {"code": code, "field": field}
        if detail:
            issue["detail"] = detail
        issues.append(issue)
        if code not in issue_codes:
            issue_codes.append(code)

    if completion_status["status"] != "required_proofs_accepted":
        add_issue("completion_status_not_accepted", "completion_status")

    if not isinstance(record, Mapping):
        add_issue("record_must_be_object", "$")
        for secret_path in _provider_proof_record_secret_paths(record):
            add_issue("token_shaped_value_detected", secret_path)
        return {
            **base_payload,
            "status": "invalid_closure_review",
            "review_decision": None,
            "blocker_state_update_allowed_after_review": False,
            "issue_codes": issue_codes,
            "issues": issues,
        }

    for secret_path in _provider_proof_record_secret_paths(record):
        add_issue("token_shaped_value_detected", secret_path)

    required_fields = [
        "run_id",
        "review_timestamp",
        "reviewer",
        "review_decision",
        "completion_status",
        "accepted_proofs",
        "accepted_record_sources",
        "review_requirements",
        "state_update_candidates_after_review",
        "secret_redaction_check",
        "review_notes",
    ]
    for field in required_fields:
        value = record.get(field)
        if field not in record or value is None or value == "":
            add_issue("missing_required_field", field)
        elif _provider_proof_record_template_placeholder(value):
            add_issue("template_placeholder_not_replaced", field)

    if record.get("run_id") != completion_status["run_id"]:
        add_issue("run_id_mismatch", "run_id")
    if record.get("completion_status") != "required_proofs_accepted":
        add_issue("completion_status_mismatch", "completion_status")

    review_timestamp = record.get("review_timestamp")
    if (
        review_timestamp is not None
        and not _provider_proof_record_template_placeholder(review_timestamp)
        and (
            not isinstance(review_timestamp, str)
            or _provider_proof_audit_validation_time(review_timestamp) is None
        )
    ):
        add_issue("invalid_review_timestamp", "review_timestamp")

    review_decision = record.get("review_decision")
    if review_decision not in {"approved", "rejected"}:
        add_issue("invalid_review_decision", "review_decision")

    if record.get("accepted_proofs") != completion_status["accepted_proofs"]:
        add_issue("accepted_proofs_mismatch", "accepted_proofs")

    packet = completion_status.get("closure_review_packet")
    if isinstance(packet, Mapping):
        if (
            record.get("accepted_record_sources")
            != packet.get("accepted_record_sources")
        ):
            add_issue("accepted_record_sources_mismatch", "accepted_record_sources")
        if (
            record.get("state_update_candidates_after_review")
            != packet.get("state_update_candidates_after_review")
        ):
            add_issue(
                "state_update_candidates_mismatch",
                "state_update_candidates_after_review",
            )
        expected_requirements = packet.get("review_requirements")
    else:
        expected_requirements = None
    if not isinstance(expected_requirements, list):
        expected_requirements = []

    review_requirements = record.get("review_requirements")
    if not isinstance(review_requirements, Mapping):
        add_issue("review_requirements_must_be_object", "review_requirements")
    else:
        rejected_requirement_count = 0
        for requirement in expected_requirements:
            value = review_requirements.get(requirement)
            if value not in {"confirmed", "rejected"}:
                add_issue(
                    "invalid_review_requirement_value",
                    "review_requirements",
                    str(requirement),
                )
            elif review_decision == "approved" and value != "confirmed":
                add_issue(
                    "review_requirement_not_confirmed",
                    "review_requirements",
                    str(requirement),
                )
            elif value == "rejected":
                rejected_requirement_count += 1
        unexpected_values = [
            key
            for key, value in review_requirements.items()
            if value not in {"confirmed", "rejected"}
        ]
        if unexpected_values:
            add_issue(
                "invalid_review_requirement_value",
                "review_requirements",
                f"{len(unexpected_values)} review requirement values are invalid",
            )
        if review_decision == "rejected" and rejected_requirement_count == 0:
            add_issue(
                "rejected_review_requires_rejected_requirement",
                "review_requirements",
            )

    if record.get("secret_redaction_check") != "passed":
        add_issue("secret_redaction_check_not_passed", "secret_redaction_check")

    approved = review_decision == "approved"
    valid = not issue_codes
    status = (
        "valid_approved_closure_review"
        if valid and approved
        else "valid_rejected_closure_review"
        if valid
        else "invalid_closure_review"
    )
    return {
        **base_payload,
        "status": status,
        "review_decision": review_decision,
        "blocker_state_update_allowed_after_review": bool(valid and approved),
        "issue_codes": issue_codes,
        "issues": issues,
    }


def _print_provider_proof_closure_review_validation(
    args: argparse.Namespace,
) -> None:
    record, error_payload = _load_provider_proof_closure_review_from_path(args)
    if error_payload is not None:
        print(json.dumps(error_payload, indent=2, sort_keys=True))
        return
    payload = _provider_proof_closure_review_validation_payload(args, record)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _provider_proof_closure_review_status_payload(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    proof_args = argparse.Namespace(
        env_example_path=args.env_example_path,
        checked_at=args.checked_at,
        run_id=args.run_id,
        audit_target=getattr(args, "proof_audit_target", None),
    )
    completion_status = _provider_proof_completion_status_payload(
        proof_args,
        env_values=env_values,
    )
    review_targets = _provider_proof_record_audit_targets(args)
    proof_targets = _provider_proof_record_audit_targets(proof_args)
    base_payload: dict[str, object] = {
        "artifact": "agent-studio-provider-proof-closure-review-status",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": completion_status["checked_at"],
        "run_id": completion_status["run_id"],
        "run_id_state": completion_status["run_id_state"],
        "completion_status": completion_status["status"],
        "audit_targets": [
            _provider_proof_portable_path_text(target) for target in review_targets
        ],
        "proof_audit_targets": [
            _provider_proof_portable_path_text(target) for target in proof_targets
        ],
        "state_change_allowed": False,
        "blocker_state_update_allowed_after_review": False,
        "latest_closure_review": None,
        "state_update_candidates_after_review": [],
        "next_action": "resolve_closure_review_and_recheck",
        "next_action_commands": [],
    }
    if completion_status["status"] != "required_proofs_accepted":
        return {
            **base_payload,
            "status": "blocked_by_completion_status",
            "next_action": "capture_validate_record_and_recheck",
            "issue_codes": ["completion_status_not_accepted"],
            "issues": [
                {
                    "code": "completion_status_not_accepted",
                    "field": "completion_status",
                    "detail": (
                        "closure review status requires provider proof "
                        "completion status to be required_proofs_accepted"
                    ),
                }
            ],
        }

    packet = completion_status.get("closure_review_packet")
    if not isinstance(packet, Mapping):
        raise TypeError("closure_review_packet must be a mapping")
    review_requirements = packet.get("review_requirements")
    if not isinstance(review_requirements, list):
        raise TypeError("closure_review_packet review_requirements must be a list")
    state_update_candidates = packet.get("state_update_candidates_after_review")
    if not isinstance(state_update_candidates, list):
        raise TypeError(
            "closure_review_packet state_update_candidates_after_review must be a list"
        )
    expected_proofs = completion_status.get("accepted_proofs")
    if not isinstance(expected_proofs, list):
        expected_proofs = []
    expected_proof_names = [str(proof) for proof in expected_proofs]
    expected_review_requirement_count = len(review_requirements)

    missing_targets: list[str] = []
    invalid_targets: list[str] = []
    readable_targets: list[str] = []
    missing_sources: list[str] = []
    secret_sources: list[str] = []
    invalid_sources: list[str] = []
    approved_sources: list[str] = []
    rejected_sources: list[str] = []
    latest_review: dict[str, object] | None = None
    latest_key: tuple[datetime, int] | None = None

    for target_index, target in enumerate(review_targets):
        target_text = _provider_proof_portable_path_text(target)
        if not target.exists():
            missing_targets.append(target_text)
            continue
        if not target.is_file():
            invalid_targets.append(target_text)
            continue
        try:
            body = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            invalid_targets.append(target_text)
            continue

        readable_targets.append(target_text)
        note_status = _provider_proof_latest_closure_review_audit_note(
            body,
            run_id=str(completion_status["run_id"]),
            expected_proofs=expected_proof_names,
            expected_review_requirement_count=expected_review_requirement_count,
        )
        if note_status is None:
            missing_sources.append(target_text)
            continue

        status = str(note_status["status"])
        source_targets = [target_text]
        if status == "approved":
            approved_sources.append(target_text)
        elif status == "rejected":
            rejected_sources.append(target_text)
        elif status == "secret_shape_detected":
            secret_sources.append(target_text)
        elif status == "invalid_fields_detected":
            invalid_sources.append(target_text)

        review_time = note_status.get("review_time")
        if not isinstance(review_time, datetime):
            review_time = datetime.min.replace(tzinfo=timezone.utc)
        candidate_key = (review_time, target_index)
        if status in {"approved", "rejected"} and (
            latest_key is None or candidate_key > latest_key
        ):
            latest_key = candidate_key
            latest_review = {
                "review_timestamp": note_status["review_timestamp"],
                "reviewer": note_status["reviewer"],
                "review_decision": note_status["review_decision"],
                "validation_status": note_status["validation_status"],
                "source_targets": source_targets,
            }

    issue_codes: list[str] = []
    issues: list[dict[str, str]] = []

    def add_issue(code: str, field: str, detail: str) -> None:
        if code not in issue_codes:
            issue_codes.append(code)
            issues.append({"code": code, "field": field, "detail": detail})

    if secret_sources:
        add_issue(
            "closure_review_audit_note_secret_shape_detected",
            "audit_targets",
            "one or more closure-review audit notes contains a token-shaped value",
        )
    if invalid_sources:
        add_issue(
            "closure_review_audit_note_invalid_fields",
            "audit_targets",
            "one or more latest closure-review audit notes has invalid fields",
        )
    if rejected_sources:
        add_issue(
            "latest_closure_review_rejected",
            "audit_targets",
            "the latest valid closure review rejects blocker-state updates",
        )
    if (
        not approved_sources
        and not rejected_sources
        and not invalid_sources
        and not secret_sources
    ):
        add_issue(
            "closure_review_missing",
            "audit_targets",
            "no valid closure-review audit note exists for this run id",
        )
    elif missing_sources:
        add_issue(
            "closure_review_coverage_incomplete",
            "audit_targets",
            "one or more readable review audit targets lacks a closure review",
        )
    if missing_targets:
        add_issue(
            "closure_review_audit_targets_missing",
            "audit_targets",
            "one or more configured closure-review audit targets does not exist",
        )
    if invalid_targets:
        add_issue(
            "closure_review_audit_targets_invalid",
            "audit_targets",
            "one or more configured closure-review audit targets is not readable",
        )

    if secret_sources:
        status = "blocked_by_secret_shaped_closure_review"
    elif invalid_sources:
        status = "blocked_by_invalid_closure_review_audit_note"
    elif rejected_sources:
        status = "blocked_by_rejected_closure_review"
    elif not approved_sources:
        status = "blocked_by_missing_closure_review"
    elif missing_sources:
        status = "blocked_by_incomplete_closure_review_coverage"
    elif invalid_targets:
        status = "blocked_by_invalid_closure_review_audit_target"
    elif missing_targets:
        status = "blocked_by_missing_closure_review_audit_target"
    else:
        status = "closure_review_approved"

    return {
        **base_payload,
        "status": status,
        "next_action": (
            "record_blocker_state_update"
            if status == "closure_review_approved"
            else "resolve_closure_review_and_recheck"
        ),
        "next_action_commands": (
            _proof_blocker_state_update_record_commands(
                str(completion_status["run_id"]),
                [
                    _provider_proof_output_path_text(target)
                    for target in proof_targets
                ],
                [
                    _provider_proof_output_path_text(target)
                    for target in review_targets
                ],
                [
                    _provider_proof_output_path_text(target)
                    for target in (
                        getattr(args, "blocker_update_audit_target", None) or []
                    )
                ],
            )
            if status == "closure_review_approved"
            else []
        ),
        "issue_codes": issue_codes,
        "issues": issues,
        "latest_closure_review": latest_review,
        "state_update_candidates_after_review": state_update_candidates,
        "readable_audit_targets": readable_targets,
        "missing_audit_targets": missing_targets,
        "invalid_audit_targets": invalid_targets,
        "missing_closure_review_targets": missing_sources,
        "approved_closure_review_targets": approved_sources,
        "rejected_closure_review_targets": rejected_sources,
        "secret_shaped_closure_review_targets": secret_sources,
        "invalid_closure_review_targets": invalid_sources,
        "blocker_state_update_allowed_after_review": status
        == "closure_review_approved",
    }


def _print_provider_proof_closure_review_status(
    args: argparse.Namespace,
) -> None:
    payload = _provider_proof_closure_review_status_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _record_provider_proof_blocker_state_update_payload(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    status = _provider_proof_closure_review_status_payload(
        argparse.Namespace(
            env_example_path=args.env_example_path,
            checked_at=args.checked_at,
            run_id=args.run_id,
            proof_audit_target=getattr(args, "proof_audit_target", None),
            audit_target=getattr(args, "closure_review_audit_target", None),
        ),
        env_values=env_values,
    )
    base_payload: dict[str, object] = {
        "artifact": "agent-studio-provider-proof-blocker-state-update-audit",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": status["checked_at"],
        "run_id": status["run_id"],
        "closure_review_status": status["status"],
        "state_change_allowed": False,
        "blocker_state_update_note_recorded": False,
        "goal_completion_claimed": False,
        "written_targets": [],
        "existing_targets": [],
    }
    if status["status"] != "closure_review_approved":
        return {
            **base_payload,
            "status": "blocked_by_closure_review_status",
            "issue_codes": ["closure_review_not_approved"],
            "issues": [
                {
                    "code": "closure_review_not_approved",
                    "field": "closure_review_status",
                    "detail": (
                        "blocker-state update notes require latest valid "
                        "approved closure-review status"
                    ),
                }
            ],
        }

    latest_review = status.get("latest_closure_review")
    candidates = status.get("state_update_candidates_after_review")
    if not isinstance(latest_review, Mapping):
        raise TypeError("latest_closure_review must be a mapping")
    if not isinstance(candidates, list):
        raise TypeError("state_update_candidates_after_review must be a list")

    targets = _provider_proof_record_audit_targets(args)
    audit_issues, audit_issue_codes = _provider_proof_audit_target_issues(targets)
    if audit_issues:
        return {
            **base_payload,
            "status": "audit_target_unwritable",
            "audit_issue_codes": audit_issue_codes,
            "audit_issues": audit_issues,
        }
    note = _provider_proof_blocker_state_update_audit_note(status)
    idempotency_key = _provider_proof_blocker_state_update_idempotency_key(status)
    existing_targets: list[str] = []
    write_targets: list[Path] = []
    for target in targets:
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        if f"- idempotency_key: {idempotency_key}" in existing:
            existing_targets.append(_provider_proof_output_path_text(target))
        else:
            write_targets.append(target)
    if targets and not write_targets:
        return {
            **base_payload,
            "boundary": "no_secret_values_printed_review_approved_update_note",
            "status": "already_recorded",
            "blocker_state_update_note_recorded": True,
            "blocker_state_update_allowed_by_review": True,
            "updated_blockers": [
                str(candidate.get("blocker"))
                for candidate in candidates
                if isinstance(candidate, Mapping)
            ],
            "latest_closure_review": {
                "review_timestamp": latest_review.get("review_timestamp"),
                "reviewer": latest_review.get("reviewer"),
                "review_decision": latest_review.get("review_decision"),
                "validation_status": latest_review.get("validation_status"),
            },
            "existing_targets": existing_targets,
        }

    for target in write_targets:
        _append_provider_proof_record_audit_note(target, note)

    return {
        **base_payload,
        "boundary": "no_secret_values_printed_review_approved_update_note",
        "status": "audit_recorded",
        "blocker_state_update_note_recorded": True,
        "blocker_state_update_allowed_by_review": True,
        "updated_blockers": [
            str(candidate.get("blocker"))
            for candidate in candidates
            if isinstance(candidate, Mapping)
        ],
        "latest_closure_review": {
            "review_timestamp": latest_review.get("review_timestamp"),
            "reviewer": latest_review.get("reviewer"),
            "review_decision": latest_review.get("review_decision"),
            "validation_status": latest_review.get("validation_status"),
        },
        "written_targets": [
            _provider_proof_portable_path_text(target) for target in write_targets
        ],
        "existing_targets": existing_targets,
    }


def _print_record_provider_proof_blocker_state_update(
    args: argparse.Namespace,
) -> None:
    payload = _record_provider_proof_blocker_state_update_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _provider_proof_json_object(path: Path) -> dict[str, object]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _provider_proof_ready_voice_items(
    output_dir: Path,
    provider_readiness: Mapping[str, object],
    voice_runtime: Mapping[str, object],
) -> list[str]:
    ready_items: list[str] = []
    if (output_dir / "product-run.preflight.json").exists():
        ready_items.append("product_run_preflight")
    workspace_validation = _provider_proof_json_object(
        output_dir / "workspace-validation.json"
    )
    if workspace_validation.get("status") == "valid_workspace":
        ready_items.append("workspace_validation")

    check_map = {
        "livekit-transport": "local_livekit_transport",
        "livekit-agent-participant": "livekit_agent_participant_startup",
        "kokoro-tts": "local_kokoro_tts",
        "rust-voice-edge": "rust_voice_edge",
        "voice-context-pruning": "voice_context_pruning",
    }
    checks = voice_runtime.get("checks")
    if isinstance(checks, list):
        by_check_id = {
            str(check.get("check_id")): check
            for check in checks
            if isinstance(check, Mapping)
        }
        for check_id, ready_item in check_map.items():
            check = by_check_id.get(check_id)
            if isinstance(check, Mapping) and check.get("status") == "ready":
                ready_items.append(ready_item)

    providers = provider_readiness.get("providers")
    if isinstance(providers, list):
        for provider in providers:
            if not isinstance(provider, Mapping):
                continue
            if (
                provider.get("provider_id") == "openrouter-livekit"
                and provider.get("status") == "ready"
            ):
                ready_items.append("openrouter_livekit_provider_readiness")
                break
    return ready_items


def _provider_proof_ready_publication_items(output_dir: Path) -> list[str]:
    ready_items: list[str] = []
    if (output_dir / "product-run.preflight.json").exists():
        ready_items.append("product_run_preflight")
    workspace_validation = _provider_proof_json_object(
        output_dir / "workspace-validation.json"
    )
    if workspace_validation.get("status") == "valid_workspace":
        ready_items.append("workspace_validation")
    if (output_dir / "publication-fixture.artifact.json").exists():
        ready_items.append("approved_local_fixture_artifact")
    if (output_dir / "source-ledger.json").exists():
        ready_items.append("source_ledger")
    if (output_dir / "publication-fixture.guardrail-audit.json").exists():
        ready_items.append("guardrail_audit")
    return ready_items


def _provider_proof_voice_blocker(
    voice_runtime: Mapping[str, object],
    *,
    configured_operator_input_fields: Sequence[str] | None = None,
) -> dict[str, object]:
    missing_inputs = [
        "OPENROUTER_API_KEY or OPENROUTER_API_KEY_FILE",
        "OPENROUTER_LIVEKIT_URL",
        "LIVEKIT_API_KEY or LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET or LIVEKIT_API_SECRET_FILE",
    ]
    configured_fields = {str(field) for field in configured_operator_input_fields or []}
    status = "unknown"
    checks = voice_runtime.get("checks")
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, Mapping):
                continue
            if check.get("check_id") != "openrouter-live-dialogue-reasoning":
                continue
            status = str(check.get("status") or "unknown")
            raw_missing = check.get("missing_env")
            if isinstance(raw_missing, list):
                normalized: list[str] = []
                if "OPENROUTER_API_KEY" in raw_missing:
                    normalized.append(
                        "OPENROUTER_API_KEY or OPENROUTER_API_KEY_FILE"
                    )
                if "OPENROUTER_LIVEKIT_URL" in raw_missing:
                    normalized.append("OPENROUTER_LIVEKIT_URL")
                if "LIVEKIT_API_KEY" in raw_missing:
                    normalized.append("LIVEKIT_API_KEY or LIVEKIT_API_KEY_FILE")
                if "LIVEKIT_API_SECRET" in raw_missing:
                    normalized.append(
                        "LIVEKIT_API_SECRET or LIVEKIT_API_SECRET_FILE"
                    )
                if normalized:
                    missing_inputs = normalized
            break
    if "OPENROUTER_API_KEY_FILE" in configured_fields:
        missing_inputs = [
            item
            for item in missing_inputs
            if item != "OPENROUTER_API_KEY or OPENROUTER_API_KEY_FILE"
        ]
    if "LIVEKIT_API_KEY_FILE" in configured_fields:
        missing_inputs = [
            item for item in missing_inputs if item != "LIVEKIT_API_KEY or LIVEKIT_API_KEY_FILE"
        ]
    if "LIVEKIT_API_SECRET_FILE" in configured_fields:
        missing_inputs = [
            item
            for item in missing_inputs
            if item != "LIVEKIT_API_SECRET or LIVEKIT_API_SECRET_FILE"
        ]
    if "OPENROUTER_LIVEKIT_URL" in configured_fields:
        missing_inputs = [
            item for item in missing_inputs if item != "OPENROUTER_LIVEKIT_URL"
        ]
    return {
        "blocker_id": "openrouter-live-dialogue-reasoning",
        "status": status,
        "type": "external_provider_input",
        "missing_inputs": missing_inputs,
        "required_evidence_after_unblock": [
            "valid provider-backed live voice preflight validation",
            "same-run OpenRouter DeepSeek live dialogue reasoning evidence",
            "same-run realtime session or LiveKit room evidence",
            "provider smoke ledger evidence",
            "realtime voice timing ledger evidence",
            "zero failed post-capture validation checks",
            "passed secret-redaction check",
        ],
    }


def _provider_proof_voice_timing_blocker(
    timing_ledger: Mapping[str, object],
) -> dict[str, object] | None:
    status = str(timing_ledger.get("status") or "missing_timing_ledger")
    if status == "ready":
        return None

    missing_inputs: list[str] = []
    raw_actions = timing_ledger.get("recommended_next_actions")
    if isinstance(raw_actions, list):
        for raw_action in raw_actions:
            action = str(raw_action)
            if action and action not in missing_inputs:
                missing_inputs.append(action)
    if not missing_inputs:
        raw_stages = timing_ledger.get("stages")
        if isinstance(raw_stages, list):
            for raw_stage in raw_stages:
                if not isinstance(raw_stage, Mapping):
                    continue
                raw_missing = raw_stage.get("missing_evidence")
                if not isinstance(raw_missing, list):
                    continue
                for raw_item in raw_missing:
                    item = str(raw_item)
                    if item and item not in missing_inputs:
                        missing_inputs.append(item)
    if not missing_inputs:
        missing_inputs.append("realtime_voice_timing_ledger status ready")

    return {
        "blocker_id": "realtime-voice-timing-ledger-evidence",
        "status": status,
        "type": "live_voice_runtime_evidence",
        "missing_inputs": missing_inputs,
        "required_evidence_after_unblock": [
            "realtime_voice_timing_ledger status ready",
            "measured LiveKit media bridge stage",
            "measured user speech start stage",
            "measured OpenRouter turn-start and generation-start stages",
            "measured first OpenRouter text delta and first Kokoro audio output",
            "measured barge-in cancellation or explicit stop-output acknowledgement",
        ],
    }


def _provider_proof_publication_blocker(
    publish_readiness: Mapping[str, object],
) -> dict[str, object]:
    platform = "linkedin"
    status = str(publish_readiness.get("status") or "unknown")
    checks = publish_readiness.get("publish_channel_checks")
    if isinstance(checks, list):
        for check in checks:
            if isinstance(check, Mapping) and check.get("platform"):
                platform = str(check["platform"])
                break
    platform_label = platform.upper()
    platform_name = "LinkedIn" if platform == "linkedin" else platform.title()
    missing_credential = f"{platform_label}_ACCESS_TOKEN or {platform_label}_ACCESS_TOKEN_FILE"
    return {
        "blocker_id": f"{platform}-publication-readiness",
        "status": status,
        "type": "external_platform_input",
        "missing_inputs": [
            missing_credential,
            f"{platform_name} policy and account-permission acknowledgement",
            "durable external destination URL or platform id",
            "rollback or postcondition evidence",
        ],
        "required_evidence_after_unblock": [
            "valid external publication preflight validation",
            f"destination channel and durable URL linked to validated {platform} readiness",
            "durable external destination proof",
            "policy acknowledgement artifact",
            "rollback or postcondition artifact",
            "zero failed post-capture validation checks",
            "passed secret-redaction check",
        ],
    }


def _provider_proof_capture_commands_after_unblock(
    proof_name: str,
    run_id: str,
    output_dir: Path,
) -> list[str]:
    command_output_dir = Path(_provider_proof_command_path_text(output_dir))
    preflight_validation_path = (
        command_output_dir / f"{proof_name}.preflight-validation.json"
    )
    workspace_validation_path = command_output_dir / "workspace-validation.json"
    return [
        *_proof_preflight_capture_commands_for_output(
            proof_name,
            run_id,
            command_output_dir,
            acknowledge_publish_channel_policy=(
                proof_name == "external-publication-proof"
            ),
        ),
        *_proof_preflight_validation_capture_commands_for_output(
            proof_name,
            run_id,
            command_output_dir,
        ),
        *_proof_execution_capture_commands_for_output(
            proof_name,
            run_id,
            command_output_dir,
        ),
        *_proof_record_template_commands(proof_name, run_id),
        *_proof_record_next_commands(
            proof_name,
            run_id,
            preflight_validation_path=preflight_validation_path,
            workspace_validation_path=workspace_validation_path,
        ),
    ]


def _provider_proof_current_gate_completion_commands(
    *,
    completion_next_action: str,
    base_commands: list[str],
    latest_failed_proofs: list[object],
    run_id: str,
    output_dir: Path,
    operator_input_readiness: Mapping[str, object] | None = None,
) -> list[str]:
    if completion_next_action != "capture_validate_record_and_recheck":
        return base_commands
    proof_names: list[str] = []
    for raw_proof_name in latest_failed_proofs:
        proof_name = str(raw_proof_name)
        if proof_name and proof_name not in proof_names:
            proof_names.append(proof_name)
    if not proof_names:
        return base_commands

    commands: list[str] = []
    for proof_name in proof_names:
        gate_commands = _provider_proof_operator_input_gate_commands_for_proof(
            proof_name,
            run_id,
            output_dir,
            operator_input_readiness=operator_input_readiness,
        )
        commands.extend(
            gate_commands
            or _provider_proof_capture_commands_after_unblock(
                proof_name,
                run_id,
                output_dir,
            )
        )

    completion_status_commands = [
        _proof_completion_status_command_with_output_dir(command, output_dir)
        for command in base_commands
        if " provider-proof-completion-status " in command
    ]
    if not completion_status_commands:
        completion_status_commands = _proof_completion_status_commands(
            run_id,
            output_dir=output_dir,
        )
    commands.extend(completion_status_commands)

    deduped_commands: list[str] = []
    for command in commands:
        if command not in deduped_commands:
            deduped_commands.append(command)
    return deduped_commands


def _provider_proof_current_blocker_matrix_payload(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> dict[str, object]:
    del env_values
    output_dir = getattr(args, "output_dir", None)
    if output_dir is None:
        output_dir = Path(f"social_media_optimiser/output/provider-proof/{args.run_id}")

    completion = _provider_proof_json_object(output_dir / "completion-status.json")
    closure_template = _provider_proof_json_object(
        output_dir / "closure-review-template.json"
    )
    closure_status = _provider_proof_json_object(output_dir / "closure-review-status.json")
    blocker_update = _provider_proof_json_object(output_dir / "blocker-state-update.json")
    provider_readiness = _provider_proof_json_object(
        output_dir / "provider-readiness.preflight.json"
    )
    voice_runtime = _provider_proof_json_object(
        output_dir / "voice-runtime-readiness.preflight.json"
    )
    realtime_voice_timing = _provider_proof_json_object(
        output_dir / "realtime-voice-timing-ledger.json"
    )
    publish_readiness = _provider_proof_json_object(
        output_dir / "publish-readiness.preflight.json"
    )
    operator_input_readiness = _provider_proof_json_object(
        output_dir / "operator-input-readiness.json"
    )

    completion_status = str(completion.get("status", "missing_completion_status"))
    latest_failed_proofs = completion.get("latest_failed_proofs", [])
    if not isinstance(latest_failed_proofs, list):
        latest_failed_proofs = []
    incomplete_audit_target_proofs = completion.get(
        "incomplete_audit_target_proofs",
        [],
    )
    if not isinstance(incomplete_audit_target_proofs, list):
        incomplete_audit_target_proofs = []
    invalid_accepted_audit_note_proofs = completion.get(
        "invalid_accepted_audit_note_proofs",
        [],
    )
    if not isinstance(invalid_accepted_audit_note_proofs, list):
        invalid_accepted_audit_note_proofs = []
    secret_shaped_audit_note_proofs = completion.get(
        "secret_shaped_audit_note_proofs",
        [],
    )
    if not isinstance(secret_shaped_audit_note_proofs, list):
        secret_shaped_audit_note_proofs = []
    missing_accepted_proofs = completion.get("missing_accepted_proofs", [])
    if not isinstance(missing_accepted_proofs, list):
        missing_accepted_proofs = []
    issue_codes = completion.get("issue_codes", [])
    if not isinstance(issue_codes, list):
        issue_codes = []
    completion_next_action = str(
        completion.get("next_action", "inspect_completion_status")
    )
    raw_completion_next_action_commands = completion.get("next_action_commands", [])
    completion_next_action_commands = (
        [
            str(command)
            for command in raw_completion_next_action_commands
            if isinstance(command, str) and command
        ]
        if isinstance(raw_completion_next_action_commands, list)
        else []
    )
    completion_next_action_commands = _provider_proof_current_gate_completion_commands(
        completion_next_action=completion_next_action,
        base_commands=completion_next_action_commands,
        latest_failed_proofs=latest_failed_proofs,
        run_id=str(args.run_id),
        output_dir=output_dir,
        operator_input_readiness=operator_input_readiness,
    )

    accepted_proofs = completion.get("accepted_proofs", [])
    if not isinstance(accepted_proofs, list):
        accepted_proofs = []
    accepted_proof_names = {str(proof) for proof in accepted_proofs}
    latest_failed_proof_names = {str(proof) for proof in latest_failed_proofs}
    incomplete_audit_target_proof_names = {
        str(proof) for proof in incomplete_audit_target_proofs
    }
    invalid_accepted_audit_note_proof_names = {
        str(proof) for proof in invalid_accepted_audit_note_proofs
    }
    secret_shaped_audit_note_proof_names = {
        str(proof) for proof in secret_shaped_audit_note_proofs
    }
    raw_accepted_record_sources = completion.get("accepted_record_sources", {})
    accepted_record_sources: dict[str, list[str]] = {}
    if isinstance(raw_accepted_record_sources, Mapping):
        for proof_name, raw_sources in raw_accepted_record_sources.items():
            if isinstance(raw_sources, list):
                accepted_record_sources[str(proof_name)] = [
                    str(source) for source in raw_sources
                ]
    raw_completion_proofs = completion.get("proofs", {})
    completion_proofs: dict[str, Mapping[str, object]] = {}
    if isinstance(raw_completion_proofs, Mapping):
        for proof_name, raw_proof in raw_completion_proofs.items():
            if isinstance(raw_proof, Mapping):
                completion_proofs[str(proof_name)] = raw_proof

    def proof_completion_status(proof_name: str) -> str:
        proof_payload = completion_proofs.get(proof_name, {})
        raw_status = proof_payload.get("status")
        if isinstance(raw_status, str):
            return raw_status
        if proof_name in latest_failed_proof_names:
            return "latest_record_failed"
        if proof_name in secret_shaped_audit_note_proof_names:
            return "latest_record_contains_secret_shape"
        if proof_name in invalid_accepted_audit_note_proof_names:
            return "latest_record_has_invalid_fields"
        if proof_name in incomplete_audit_target_proof_names:
            return "accepted_record_missing_from_some_targets"
        if (
            proof_name in accepted_proof_names
            and completion_status == "required_proofs_accepted"
        ):
            return "accepted_record_found"
        if proof_name in accepted_proof_names:
            return "accepted_record_missing_from_some_targets"
        return "missing_accepted_record"

    def proof_record_outcome(proof_status: str) -> str:
        if proof_status == "latest_record_failed":
            return "failed"
        if proof_status == "accepted_record_found":
            return "accepted"
        if proof_status == "accepted_record_missing_from_some_targets":
            return "incomplete"
        if proof_status in {
            "latest_record_contains_secret_shape",
            "latest_record_has_invalid_fields",
        }:
            return "invalid"
        return "missing"

    voice_completion_status = proof_completion_status(
        "provider-backed-live-voice-proof"
    )
    publication_completion_status = proof_completion_status(
        "external-publication-proof"
    )
    voice_outcome = proof_record_outcome(voice_completion_status)
    publication_outcome = proof_record_outcome(publication_completion_status)

    def proof_current_state(
        proof_status: str,
        *,
        blocked_state: str,
    ) -> str:
        if proof_status == "accepted_record_found":
            return "accepted_proof_record_available"
        if proof_status in {
            "accepted_record_missing_from_some_targets",
            "latest_record_contains_secret_shape",
            "latest_record_has_invalid_fields",
        }:
            return proof_status
        return blocked_state

    def proof_completion_status_blocker(
        proof_name: str,
        proof_status: str,
    ) -> dict[str, object]:
        proof_payload = completion_proofs.get(proof_name, {})
        if proof_status == "accepted_record_missing_from_some_targets":
            raw_targets = proof_payload.get("missing_source_targets", [])
            missing_targets = [
                str(target) for target in raw_targets
            ] if isinstance(raw_targets, list) else []
            return {
                "blocker_id": "accepted-record-audit-target-coverage",
                "type": "audit_target_coverage",
                "missing_inputs": missing_targets
                or ["accepted record in every configured audit target"],
                "required_evidence_after_unblock": [
                    "accepted proof record present in every configured audit target",
                    "provider-proof-completion-status reports required_proofs_accepted",
                ],
            }
        if proof_status == "latest_record_contains_secret_shape":
            return {
                "blocker_id": "accepted-record-secret-shape",
                "type": "audit_note_redaction",
                "missing_inputs": ["secret-free accepted proof audit note"],
                "required_evidence_after_unblock": [
                    "latest accepted proof audit note contains no token-shaped values",
                    "provider-proof-completion-status reports no secret-shaped audit notes",
                ],
            }
        return {
            "blocker_id": "accepted-record-invalid-fields",
            "type": "audit_note_validation",
            "missing_inputs": ["valid accepted proof audit note fields"],
            "required_evidence_after_unblock": [
                "latest accepted proof audit note passes schema-backed validation",
                "provider-proof-completion-status reports no invalid accepted audit notes",
            ],
        }

    def proof_remaining_blockers(
        proof_name: str,
        proof_status: str,
        default_blocker: dict[str, object],
    ) -> list[dict[str, object]]:
        if proof_status == "accepted_record_found":
            return []
        if proof_status in {
            "accepted_record_missing_from_some_targets",
            "latest_record_contains_secret_shape",
            "latest_record_has_invalid_fields",
        }:
            return [proof_completion_status_blocker(proof_name, proof_status)]
        if (
            default_blocker.get("status") == "ready"
            and not default_blocker.get("missing_inputs")
        ):
            return []
        return [default_blocker]

    def proof_evidence_refs(
        proof_name: str,
        proof_status: str,
        blocked_refs: list[str],
    ) -> list[str]:
        if proof_status == "accepted_record_found":
            return [
                "completion-status.json",
                *accepted_record_sources.get(proof_name, []),
            ]
        if proof_status in {
            "accepted_record_missing_from_some_targets",
            "latest_record_contains_secret_shape",
            "latest_record_has_invalid_fields",
        }:
            proof_payload = completion_proofs.get(proof_name, {})
            refs = ["completion-status.json"]
            for field in [
                "source_targets",
                "missing_source_targets",
                "secret_source_targets",
                "invalid_source_targets",
            ]:
                raw_refs = proof_payload.get(field, [])
                if isinstance(raw_refs, list):
                    refs.extend(str(ref) for ref in raw_refs)
            return refs
        return blocked_refs

    proof_completion_statuses = {
        "provider-backed-live-voice-proof": voice_completion_status,
        "external-publication-proof": publication_completion_status,
    }

    def completion_blocker_proofs(
        raw_proofs: list[object],
        proof_status: str,
    ) -> list[str]:
        proof_names = [str(proof) for proof in raw_proofs]
        for proof_name, current_status in proof_completion_statuses.items():
            if current_status == proof_status and proof_name not in proof_names:
                proof_names.append(proof_name)
        return proof_names

    completion_blocker_lists: dict[str, list[str]] = {}
    incomplete_summary_proofs = completion_blocker_proofs(
        incomplete_audit_target_proofs,
        "accepted_record_missing_from_some_targets",
    )
    if incomplete_summary_proofs:
        completion_blocker_lists["incomplete_audit_target_proofs"] = (
            incomplete_summary_proofs
        )
    secret_summary_proofs = completion_blocker_proofs(
        secret_shaped_audit_note_proofs,
        "latest_record_contains_secret_shape",
    )
    if secret_summary_proofs:
        completion_blocker_lists["secret_shaped_audit_note_proofs"] = (
            secret_summary_proofs
        )
    invalid_summary_proofs = completion_blocker_proofs(
        invalid_accepted_audit_note_proofs,
        "latest_record_has_invalid_fields",
    )
    if invalid_summary_proofs:
        completion_blocker_lists["invalid_accepted_audit_note_proofs"] = (
            invalid_summary_proofs
        )

    operator_input_issue_codes = operator_input_readiness.get("issue_codes", [])
    if not isinstance(operator_input_issue_codes, list):
        operator_input_issue_codes = []
    operator_input_issues = operator_input_readiness.get("issues", [])
    operator_input_blocked_fields: list[str] = []
    raw_operator_input_blocked_fields = operator_input_readiness.get("blocked_fields")
    if isinstance(raw_operator_input_blocked_fields, list):
        for raw_field in raw_operator_input_blocked_fields:
            field = str(raw_field)
            if field and field not in operator_input_blocked_fields:
                operator_input_blocked_fields.append(field)
    elif isinstance(operator_input_issues, list):
        for raw_issue in operator_input_issues:
            if not isinstance(raw_issue, Mapping):
                continue
            raw_field = raw_issue.get("field")
            if (
                isinstance(raw_field, str)
                and raw_field
                and raw_field not in operator_input_blocked_fields
            ):
                operator_input_blocked_fields.append(raw_field)
    operator_input_proofs: dict[str, object] = {}
    operator_input_command_path = _provider_proof_operator_input_command_path(
        operator_input_readiness,
        output_dir,
    )
    operator_input_retry_commands = _proof_operator_input_retry_commands_for_input(
        str(args.run_id),
        operator_input_command_path,
    )
    guarded_operator_input_retry_commands = (
        _proof_operator_input_retry_commands_for_input(
            str(args.run_id),
            operator_input_command_path,
            fail_on_blocked=True,
        )
    )
    strict_operator_input_readiness_command = guarded_operator_input_retry_commands[0]
    raw_operator_input_exit_policy = operator_input_readiness.get("exit_policy", {})
    operator_input_exit_policy: dict[str, object] = {}
    if isinstance(raw_operator_input_exit_policy, Mapping):
        operator_input_exit_policy = {
            str(key): value for key, value in raw_operator_input_exit_policy.items()
        }
    operator_input_status = str(
        operator_input_readiness.get(
            "status",
            "missing_operator_input_readiness",
        )
    )
    operator_input_ready_status = str(
        operator_input_exit_policy.get(
            "ready_status",
            "ready_for_credential_snapshot_refresh",
        )
    )
    operator_input_required_fields = operator_input_readiness.get("required_fields", [])
    if not isinstance(operator_input_required_fields, list):
        operator_input_required_fields = []
    operator_input_configured_fields = operator_input_readiness.get(
        "configured_fields",
        [],
    )
    if not isinstance(operator_input_configured_fields, list):
        operator_input_configured_fields = []
    operator_input_field_groups = operator_input_readiness.get("field_groups", {})
    if not isinstance(operator_input_field_groups, Mapping):
        operator_input_field_groups = {}
    operator_input_field_contracts = operator_input_readiness.get("field_contracts", {})
    if not isinstance(operator_input_field_contracts, Mapping):
        operator_input_field_contracts = {}
    operator_input_field_ownership = operator_input_readiness.get("field_ownership", {})
    if not isinstance(operator_input_field_ownership, Mapping):
        operator_input_field_ownership = {}
    operator_input_field_statuses = operator_input_readiness.get("field_statuses", {})
    if not isinstance(operator_input_field_statuses, Mapping):
        operator_input_field_statuses = {}
    raw_operator_input_effective_exit_code = operator_input_readiness.get(
        "effective_fail_on_blocked_exit_code"
    )
    operator_input_effective_exit_code = (
        raw_operator_input_effective_exit_code
        if isinstance(raw_operator_input_effective_exit_code, int)
        else _provider_proof_operator_input_effective_fail_exit_code(
            operator_input_status
        )
    )
    current_state_packets = {
        "current_blocker_matrix": "current-blocker-matrix.json",
        "current_proof_status": "current-proof-status.md",
        "operator_unblocker_checklist": "operator-unblocker-checklist.md",
    }
    current_state_packet_commands = {
        "current_blocker_matrix": _proof_current_blocker_matrix_capture_command(
            str(args.run_id),
            output_dir,
        ),
        "current_proof_status": _proof_current_status_capture_command(
            str(args.run_id),
            output_dir,
        ),
        "operator_unblocker_checklist": (
            _proof_operator_unblocker_checklist_capture_command(
                str(args.run_id),
                output_dir,
            )
        ),
    }
    next_status_packet = "current-proof-status.md"
    next_operator_packet = "operator-unblocker-checklist.md"

    raw_operator_input_proofs = operator_input_readiness.get("proofs", {})
    if isinstance(raw_operator_input_proofs, Mapping):
        for proof_name, raw_proof in raw_operator_input_proofs.items():
            if not isinstance(raw_proof, Mapping):
                continue
            proof_blocked_fields: list[str] = []
            proof_field_groups: dict[str, list[str]] = {}
            for field_name in [
                "missing_fields",
                "placeholder_fields",
                "invalid_fields",
                "unavailable_secret_file_fields",
            ]:
                raw_fields = raw_proof.get(field_name, [])
                proof_field_groups[field_name] = []
                if not isinstance(raw_fields, list):
                    continue
                for raw_field in raw_fields:
                    field = str(raw_field)
                    if field and field not in proof_field_groups[field_name]:
                        proof_field_groups[field_name].append(field)
                    if field and field not in proof_blocked_fields:
                        proof_blocked_fields.append(field)
            raw_blocked_fields = raw_proof.get("blocked_fields")
            if isinstance(raw_blocked_fields, list):
                proof_blocked_fields = []
                for raw_field in raw_blocked_fields:
                    field = str(raw_field)
                    if field and field not in proof_blocked_fields:
                        proof_blocked_fields.append(field)
            proof_configured_fields: list[str] = []
            raw_configured_fields = raw_proof.get("configured_fields")
            if isinstance(raw_configured_fields, list):
                for raw_field in raw_configured_fields:
                    field = str(raw_field)
                    if field and field not in proof_configured_fields:
                        proof_configured_fields.append(field)
            proof_required_fields: list[str] = []
            raw_required_fields = raw_proof.get("required_fields")
            if isinstance(raw_required_fields, list):
                for raw_field in raw_required_fields:
                    field = str(raw_field)
                    if field and field not in proof_required_fields:
                        proof_required_fields.append(field)
            proof_state = str(raw_proof.get("state", "unknown"))
            proof_field_contracts = _provider_proof_operator_input_field_contracts(
                str(proof_name)
            )
            raw_field_contracts = raw_proof.get("field_contracts")
            if isinstance(raw_field_contracts, Mapping):
                proof_field_contracts = {
                    str(field): str(contract)
                    for field, contract in raw_field_contracts.items()
                }
            proof_field_ownership = _provider_proof_operator_input_field_ownership(
                str(proof_name)
            )
            raw_field_ownership = raw_proof.get("field_ownership")
            if isinstance(raw_field_ownership, Mapping):
                proof_field_ownership = {
                    str(field): (
                        {
                            str(key): str(value)
                            for key, value in ownership.items()
                        }
                        if isinstance(ownership, Mapping)
                        else {
                            "proof_id": _provider_proof_operator_input_proof_id(
                                str(field)
                            ),
                            "proof_input_role": (
                                _provider_proof_operator_input_role(str(field))
                            ),
                        }
                    )
                    for field, ownership in raw_field_ownership.items()
                }
            proof_field_statuses = (
                _provider_proof_operator_input_field_statuses_from_groups(
                    str(proof_name),
                    raw_proof,
                )
            )
            raw_field_statuses = raw_proof.get("field_statuses")
            if isinstance(raw_field_statuses, Mapping):
                proof_field_statuses = {
                    str(field): (
                        {
                            str(key): str(value)
                            for key, value in status.items()
                        }
                        if isinstance(status, Mapping)
                        else {"state": str(status)}
                    )
                    for field, status in raw_field_statuses.items()
                }
            proof_issue_codes: list[str] = []
            if isinstance(operator_input_issues, list):
                for raw_issue in operator_input_issues:
                    if not isinstance(raw_issue, Mapping):
                        continue
                    raw_field = raw_issue.get("field")
                    raw_code = raw_issue.get("code")
                    if not (
                        isinstance(raw_field, str)
                        and raw_field in proof_blocked_fields
                        and isinstance(raw_code, str)
                        and raw_code
                    ):
                        continue
                    if raw_code not in proof_issue_codes:
                        proof_issue_codes.append(raw_code)
            operator_input_proofs[str(proof_name)] = {
                "state": proof_state,
                "status": (
                    operator_input_ready_status
                    if not proof_blocked_fields
                    and proof_state == "ready_for_credential_snapshot_refresh"
                    else operator_input_status
                ),
                "issue_codes": proof_issue_codes,
                "blocked_fields": proof_blocked_fields,
                "required_fields": proof_required_fields,
                "configured_fields": proof_configured_fields,
                "field_groups": proof_field_groups,
                "field_contracts": proof_field_contracts,
                "field_ownership": proof_field_ownership,
                "field_statuses": proof_field_statuses,
                "next_action": _provider_proof_operator_input_next_action(
                    str(proof_name),
                    proof_state,
                    fallback=str(
                        operator_input_readiness.get(
                            "next_action",
                            "inspect_operator_input_readiness",
                        )
                    ),
                    blocked_fields=proof_blocked_fields,
                ),
                "required_evidence_after_unblock": (
                    _provider_proof_operator_input_required_evidence(
                        str(proof_name)
                    )
                ),
                "next_action_commands": operator_input_retry_commands,
                "guarded_next_action_commands": guarded_operator_input_retry_commands,
            }

    voice_default_blocker = _provider_proof_voice_blocker(
        voice_runtime,
        configured_operator_input_fields=operator_input_proofs.get(
            "provider-backed-live-voice-proof",
            {},
        ).get("configured_fields", []),
    )
    voice_remaining_blockers = proof_remaining_blockers(
        "provider-backed-live-voice-proof",
        voice_completion_status,
        voice_default_blocker,
    )
    voice_timing_blocker = _provider_proof_voice_timing_blocker(
        realtime_voice_timing
    )
    if (
        voice_completion_status != "accepted_record_found"
        and voice_timing_blocker is not None
        and not voice_remaining_blockers
    ):
        voice_remaining_blockers = [voice_timing_blocker]

    operator_proof_packets: dict[str, object] = {}
    for proof_name, proof_readiness in operator_input_proofs.items():
        if not isinstance(proof_readiness, Mapping):
            continue
        proof_schema = (
            _voice_proof_artifact_schema()
            if proof_name == "provider-backed-live-voice-proof"
            else _publication_proof_artifact_schema()
        )
        proof_required_fields = proof_schema.get("required_fields", [])
        if not isinstance(proof_required_fields, list):
            proof_required_fields = []
        operator_proof_packets[proof_name] = {
            "proof_id": proof_name,
            "matrix_parity_ref": f"/operator_input_readiness/proofs/{proof_name}",
            "proof_capture_matrix_ref": (
                f"/proofs/{proof_name}/proof_capture_commands_after_unblock"
            ),
            "proof_plan_packet": "proof-plan.json",
            "proof_plan_packet_ref": str(
                Path(_provider_proof_command_path_text(output_dir)) / "proof-plan.json"
            ),
            "proof_plan_packet_command": operator_input_retry_commands[2],
            "proof_plan_operator_packet_ref": (
                f"/proofs/{proof_name}/operator_proof_packet"
            ),
            "proof_capture_commands_after_unblock": (
                _provider_proof_capture_commands_after_unblock(
                    proof_name,
                    str(args.run_id),
                    output_dir,
                )
            ),
            "packet_schema_version": "operator-proof-packet.v1",
            "handoff_contract": "value-free-operator-proof-handoff",
            "state_change_allowed": False,
            "state_change_guardrail": (
                "no_state_change_without_accepted_proof_and_closure_review"
            ),
            "source_artifacts": {
                "operator_input_readiness": "operator-input-readiness.json",
                "current_blocker_matrix": "current-blocker-matrix.json",
                "operator_input_template": "operator-inputs.template.env",
                "proof_plan": "proof-plan.json",
            },
            "operator_input_field_contracts": (
                _provider_proof_operator_input_field_contracts(proof_name)
            ),
            "completion_evidence_ref": "completion-status.json",
            "closure_evidence_refs": [
                "closure-review-template.json",
                "closure-review-status.json",
                "blocker-state-update.json",
            ],
            "current_state_packets": current_state_packets,
            "current_state_packet_commands": current_state_packet_commands,
            "next_status_packet": next_status_packet,
            "next_operator_packet": next_operator_packet,
            "label": _provider_proof_operator_packet_label(proof_name),
            "secret_handling": (
                "Do not print tokens, API keys, or secrets; record endpoint "
                "and account identifiers only."
            ),
            "must_capture": _provider_proof_operator_packet_must_capture(
                proof_name
            ),
            "store_in": PROVIDER_PROOF_RECORD_TARGETS,
            "proof_record_schema": proof_schema,
            "proof_record_required_fields": [
                str(field) for field in proof_required_fields
            ],
            "current_gate": {
                "completion_status": completion_status,
                "closure_review_template_status": str(
                    closure_template.get("status", "missing_closure_review_template")
                ),
                "closure_review_status": str(
                    closure_status.get("status", "missing_closure_review_status")
                ),
                "blocker_state_update_status": str(
                    blocker_update.get("status", "missing_blocker_state_update")
                ),
                "completion_next_action": completion_next_action,
                "completion_next_action_commands": completion_next_action_commands,
                "state_change_allowed": blocker_update.get("state_change_allowed")
                is True,
                "goal_completion_claimed": blocker_update.get(
                    "goal_completion_claimed"
                )
                is True,
                "completion_issue_codes": [str(code) for code in issue_codes],
                "latest_failed_proofs": [
                    str(proof) for proof in latest_failed_proofs
                ],
                "missing_accepted_proofs": [
                    str(proof) for proof in missing_accepted_proofs
                ],
            },
            "operator_input_readiness": {
                **dict(proof_readiness),
                "status": str(proof_readiness.get("status") or operator_input_status),
                "checked_at": str(
                    operator_input_readiness.get("checked_at", "unknown")
                ),
                "evidence_ref": "operator-input-readiness.json",
                "effective_fail_on_blocked_exit_code": (
                    operator_input_effective_exit_code
                ),
                "exit_policy": operator_input_exit_policy,
                "strict_readiness_command": strict_operator_input_readiness_command,
            },
        }

    return {
        "artifact": "agent-studio-current-blocker-matrix",
        "checked_at": args.checked_at or completion.get("checked_at") or date.today().isoformat(),
        "run_id": str(args.run_id),
        "boundary": "no_secret_values_no_state_change",
        "completion": {
            "status": completion_status,
            "next_action": completion_next_action,
            "next_action_commands": completion_next_action_commands,
            "latest_failed_proofs": [str(proof) for proof in latest_failed_proofs],
            "missing_accepted_proofs": [
                str(proof) for proof in missing_accepted_proofs
            ],
            **completion_blocker_lists,
            "issue_codes": [str(code) for code in issue_codes],
            "evidence_ref": "completion-status.json",
        },
        "closure": {
            "closure_review_template_status": str(
                closure_template.get("status", "missing_closure_review_template")
            ),
            "closure_review_status": str(
                closure_status.get("status", "missing_closure_review_status")
            ),
            "blocker_state_update_status": str(
                blocker_update.get("status", "missing_blocker_state_update")
            ),
            "state_change_allowed": blocker_update.get("state_change_allowed") is True,
            "goal_completion_claimed": blocker_update.get("goal_completion_claimed")
            is True,
            "evidence_refs": [
                "closure-review-template.json",
                "closure-review-status.json",
                "blocker-state-update.json",
            ],
        },
        "operator_input_readiness": {
            "status": operator_input_status,
            "checked_at": str(operator_input_readiness.get("checked_at", "unknown")),
            "issue_codes": [str(code) for code in operator_input_issue_codes],
            "blocked_fields": operator_input_blocked_fields,
            "required_fields": [str(field) for field in operator_input_required_fields],
            "configured_fields": [
                str(field) for field in operator_input_configured_fields
            ],
            "field_groups": {
                str(group): [str(field) for field in fields]
                for group, fields in operator_input_field_groups.items()
                if isinstance(fields, list)
            },
            "field_contracts": {
                str(field): str(contract)
                for field, contract in operator_input_field_contracts.items()
            },
            "field_ownership": {
                str(field): (
                    {
                        str(key): str(value)
                        for key, value in ownership.items()
                    }
                    if isinstance(ownership, Mapping)
                    else {
                        "proof_id": _provider_proof_operator_input_proof_id(
                            str(field)
                        ),
                        "proof_input_role": (
                            _provider_proof_operator_input_role(str(field))
                        ),
                    }
                )
                for field, ownership in operator_input_field_ownership.items()
            },
            "field_statuses": {
                str(field): (
                    {
                        str(key): str(value)
                        for key, value in status.items()
                    }
                    if isinstance(status, Mapping)
                    else {"state": str(status)}
                )
                for field, status in operator_input_field_statuses.items()
            },
            "strict_readiness_command": strict_operator_input_readiness_command,
            "next_action_commands": operator_input_retry_commands,
            "guarded_next_action_commands": guarded_operator_input_retry_commands,
            "exit_policy": operator_input_exit_policy,
            "effective_fail_on_blocked_exit_code": (
                operator_input_effective_exit_code
            ),
            "proofs": operator_input_proofs,
            "evidence_ref": "operator-input-readiness.json",
        },
        "operator_proof_packets": operator_proof_packets,
        "current_state_packets": current_state_packets,
        "current_state_packet_commands": current_state_packet_commands,
        "proofs": {
            "provider-backed-live-voice-proof": {
                "current_state": proof_current_state(
                    voice_completion_status,
                    blocked_state="provider_backed_live_voice_preflight_ready_record_capture_needed",
                ),
                "latest_record_outcome": voice_outcome,
                "accepted_record_available": (
                    voice_completion_status == "accepted_record_found"
                ),
                "do_not_reopen_as_blockers": _provider_proof_ready_voice_items(
                    output_dir,
                    provider_readiness,
                    voice_runtime,
                ),
                "remaining_blockers": voice_remaining_blockers,
                "proof_capture_commands_after_unblock": (
                    _provider_proof_capture_commands_after_unblock(
                        "provider-backed-live-voice-proof",
                        str(args.run_id),
                        output_dir,
                    )
                ),
                "evidence_refs": proof_evidence_refs(
                    "provider-backed-live-voice-proof",
                    voice_completion_status,
                    [
                        "provider-readiness.preflight.json",
                        "voice-runtime-readiness.preflight.json",
                        "provider-backed-live-voice-proof.preflight-validation.json",
                        "provider-backed-live-voice-proof.failed-record.json",
                        "provider-backed-live-voice-proof.failed-record-validation.json",
                        "provider-backed-live-voice-proof.failed-record-audit.json",
                        "realtime-voice-timing-ledger.json",
                    ],
                ),
            },
            "external-publication-proof": {
                "current_state": proof_current_state(
                    publication_completion_status,
                    blocked_state=(
                        "local_publication_fixture_ready_external_destination_blocked"
                    ),
                ),
                "latest_record_outcome": publication_outcome,
                "accepted_record_available": (
                    publication_completion_status == "accepted_record_found"
                ),
                "do_not_reopen_as_blockers": _provider_proof_ready_publication_items(
                    output_dir
                ),
                "remaining_blockers": proof_remaining_blockers(
                    "external-publication-proof",
                    publication_completion_status,
                    _provider_proof_publication_blocker(publish_readiness),
                ),
                "proof_capture_commands_after_unblock": (
                    _provider_proof_capture_commands_after_unblock(
                        "external-publication-proof",
                        str(args.run_id),
                        output_dir,
                    )
                ),
                "evidence_refs": proof_evidence_refs(
                    "external-publication-proof",
                    publication_completion_status,
                    [
                        "publish-readiness.preflight.json",
                        "external-publication-proof.preflight-validation.json",
                        "publication-fixture.artifact.json",
                        "publication-fixture.claim.json",
                        "publication-fixture.source.json",
                        "publication-fixture.guardrail-audit.json",
                        "source-ledger.json",
                        "external-publication-proof.failed-record.json",
                        "external-publication-proof.failed-record-validation.json",
                        "external-publication-proof.failed-record-audit.json",
                    ],
                ),
            },
        },
        "next_operator_packet": next_operator_packet,
        "next_status_packet": next_status_packet,
    }


def _print_provider_proof_current_blocker_matrix(args: argparse.Namespace) -> None:
    payload = _provider_proof_current_blocker_matrix_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _provider_proof_operator_packet_label(proof_name: str) -> str:
    if proof_name == "provider-backed-live-voice-proof":
        return "Provider-backed live voice proof packet"
    return "External publication proof packet"


def _provider_proof_operator_packet_must_capture(proof_name: str) -> list[str]:
    if proof_name == "provider-backed-live-voice-proof":
        return [
            "provider_smoke_ledger with execute_live_calls=true",
            "livekit_voice_timing_capture JSON",
            "realtime_voice_timing_ledger JSON",
            "LiveKit room/session id and participant identity",
            "captured microphone turn with first text/audio timing",
            "interrupt or barge-in acknowledgement evidence",
        ]
    return [
        (
            "approved artifact snapshot with copy, media, audience, "
            "visibility, disclosure, and schedule"
        ),
        "platform API response proof or approved manual completion proof",
        "durable platform ID or URL",
        "postcondition monitoring record",
        "rollback, delete, private, or correction proof",
    ]


def _provider_proof_operator_packet_readme_contract(
    proof_name: str,
) -> dict[str, object]:
    return {
        "label": _provider_proof_operator_packet_label(proof_name),
        "packet_schema_version": "operator-proof-packet.v1",
        "handoff_contract": "value-free-operator-proof-handoff",
        "state_change_allowed": False,
        "state_change_guardrail": (
            "no_state_change_without_accepted_proof_and_closure_review"
        ),
        "secret_handling": (
            "Do not print tokens, API keys, or secrets; record endpoint "
            "and account identifiers only."
        ),
        "next_status_packet": "current-proof-status.md",
        "next_operator_packet": "operator-unblocker-checklist.md",
        "current_gate_recovery_authority": (
            "open current_matrix_packet_ref at current_matrix_operator_packet_ref "
            "for current_gate, completion_next_action, and completion recovery commands"
        ),
        "source_artifacts": {
            "operator_input_readiness": "operator-input-readiness.json",
            "current_blocker_matrix": "current-blocker-matrix.json",
            "operator_input_template": "operator-inputs.template.env",
            "proof_plan": "proof-plan.json",
        },
        "operator_input_field_contracts": (
            _provider_proof_operator_input_field_contracts(proof_name)
        ),
        "must_capture": _provider_proof_operator_packet_must_capture(proof_name),
        "store_in": PROVIDER_PROOF_RECORD_TARGETS,
    }


def _provider_proof_operator_input_template_field_groups(
    proof_name: str,
) -> dict[str, list[str]]:
    if proof_name == "provider-backed-live-voice-proof":
        return {
            "invalid_fields": [],
            "missing_fields": [],
            "placeholder_fields": ["OPENROUTER_LIVEKIT_URL"],
            "unavailable_secret_file_fields": [
                "OPENROUTER_API_KEY_FILE",
                "LIVEKIT_API_KEY_FILE",
                "LIVEKIT_API_SECRET_FILE",
            ],
        }
    return {
        "invalid_fields": [],
        "missing_fields": [],
        "placeholder_fields": [
            "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
            "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
            "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
        ],
        "unavailable_secret_file_fields": ["LINKEDIN_ACCESS_TOKEN_FILE"],
    }


def _provider_proof_operator_input_template_readiness(
    proof_name: str,
    *,
    checked_at: str,
    command_run_id: str,
    output_dir: Path,
) -> dict[str, object]:
    state = "blocked_by_operator_inputs"
    field_groups = _provider_proof_operator_input_template_field_groups(proof_name)
    required_fields = [
        str(field)
        for field in PROVIDER_PROOF_OPERATOR_INPUT_FIELDS.get(proof_name, [])
    ]
    blocked_field_names = {
        field
        for fields in field_groups.values()
        for field in fields
    }
    blocked_fields = [
        field
        for field in PROVIDER_PROOF_OPERATOR_INPUT_FIELDS.get(proof_name, [])
        if field in blocked_field_names
    ]
    report_only_commands = [
        _proof_operator_input_readiness_capture_command(command_run_id, output_dir),
        (
            "uv run all-about-llms-admin blocker-credential-snapshot "
            f"--operator-input-path {output_dir}/operator-inputs.template.env > "
            f"{output_dir}/credential-snapshot.json"
        ),
        (
            "uv run all-about-llms-admin provider-proof-plan "
            f"--run-id {command_run_id} --operator-input-path "
            f"{output_dir}/operator-inputs.template.env > "
            f"{output_dir}/proof-plan.json"
        ),
        _proof_current_blocker_matrix_capture_command(command_run_id, output_dir),
        _proof_current_status_capture_command(command_run_id, output_dir),
        _proof_operator_unblocker_checklist_capture_command(
            command_run_id,
            output_dir,
        ),
    ]
    guarded_commands = [
        _proof_operator_input_readiness_capture_command(
            command_run_id,
            output_dir,
            fail_on_blocked=True,
        ),
        *report_only_commands[1:],
    ]
    return {
        "status": state,
        "state": state,
        "checked_at": checked_at,
        "evidence_ref": "operator-input-readiness.json",
        "next_action": _provider_proof_operator_input_next_action(
            proof_name,
            state,
            fallback="inspect_operator_input_readiness",
            blocked_fields=blocked_fields,
        ),
        "effective_fail_on_blocked_exit_code": (
            _provider_proof_operator_input_effective_fail_exit_code(state)
        ),
        "issue_codes": [
            "operator_input_secret_file_unavailable",
            "operator_input_placeholder",
        ],
        "field_groups": field_groups,
        "field_contracts": _provider_proof_operator_input_field_contracts(
            proof_name,
        ),
        "field_ownership": _provider_proof_operator_input_field_ownership(
            proof_name,
        ),
        "field_statuses": _provider_proof_operator_input_field_statuses_from_groups(
            proof_name,
            {
                **field_groups,
                "configured_fields": [],
            },
        ),
        "next_action_commands": report_only_commands,
        "guarded_next_action_commands": guarded_commands,
        "blocked_fields": blocked_fields,
        "required_fields": required_fields,
        "configured_fields": [],
        "required_evidence_after_unblock": (
            _provider_proof_operator_input_required_evidence(proof_name)
        ),
    }


def _provider_proof_operator_input_report_readiness(
    proof_name: str,
    operator_input_readiness: Mapping[str, object] | None,
    *,
    checked_at: str,
    command_run_id: str,
    output_dir: Path,
) -> dict[str, object] | None:
    if operator_input_readiness is None:
        return None
    raw_proofs = operator_input_readiness.get("proofs")
    if not isinstance(raw_proofs, Mapping):
        return None
    raw_proof = raw_proofs.get(proof_name)
    if not isinstance(raw_proof, Mapping):
        return None

    def field_list(field_name: str) -> list[str]:
        raw_fields = raw_proof.get(field_name, [])
        if not isinstance(raw_fields, list):
            return []
        fields: list[str] = []
        for raw_field in raw_fields:
            field = str(raw_field)
            if field and field not in fields:
                fields.append(field)
        return fields

    state = str(raw_proof.get("state") or operator_input_readiness.get("status"))
    if not state:
        state = "unknown"
    field_groups = {
        "invalid_fields": field_list("invalid_fields"),
        "missing_fields": field_list("missing_fields"),
        "placeholder_fields": field_list("placeholder_fields"),
        "unavailable_secret_file_fields": field_list(
            "unavailable_secret_file_fields"
        ),
    }
    blocked_fields = field_list("blocked_fields")
    if not blocked_fields:
        for fields in field_groups.values():
            for field in fields:
                if field not in blocked_fields:
                    blocked_fields.append(field)
    required_fields = field_list("required_fields") or [
        str(field)
        for field in PROVIDER_PROOF_OPERATOR_INPUT_FIELDS.get(proof_name, [])
    ]
    configured_fields = field_list("configured_fields")
    raw_field_contracts = raw_proof.get("field_contracts")
    field_contracts = (
        {str(field): str(contract) for field, contract in raw_field_contracts.items()}
        if isinstance(raw_field_contracts, Mapping)
        else _provider_proof_operator_input_field_contracts(proof_name)
    )
    raw_field_ownership = raw_proof.get("field_ownership")
    field_ownership = (
        {
            str(field): (
                {str(key): str(value) for key, value in ownership.items()}
                if isinstance(ownership, Mapping)
                else {
                    "proof_id": _provider_proof_operator_input_proof_id(str(field)),
                    "proof_input_role": _provider_proof_operator_input_role(
                        str(field)
                    ),
                }
            )
            for field, ownership in raw_field_ownership.items()
        }
        if isinstance(raw_field_ownership, Mapping)
        else _provider_proof_operator_input_field_ownership(proof_name)
    )
    raw_field_statuses = raw_proof.get("field_statuses")
    field_statuses = (
        {
            str(field): (
                {str(key): str(value) for key, value in status.items()}
                if isinstance(status, Mapping)
                else {"state": str(status)}
            )
            for field, status in raw_field_statuses.items()
        }
        if isinstance(raw_field_statuses, Mapping)
        else _provider_proof_operator_input_field_statuses_from_groups(
            proof_name,
            {
                **field_groups,
                "configured_fields": configured_fields,
            },
        )
    )
    issue_codes: list[str] = []
    for field in blocked_fields:
        raw_status = field_statuses.get(field)
        if not isinstance(raw_status, Mapping):
            continue
        issue_code = str(raw_status.get("issue_code") or "")
        if issue_code and issue_code != "none" and issue_code not in issue_codes:
            issue_codes.append(issue_code)

    def commands(field_name: str) -> list[str]:
        raw_commands = operator_input_readiness.get(field_name)
        if not isinstance(raw_commands, list):
            return []
        return [str(command) for command in raw_commands]

    next_action_commands = commands("next_action_commands")
    guarded_next_action_commands = commands("guarded_next_action_commands")
    if not next_action_commands:
        template = _provider_proof_operator_input_template_readiness(
            proof_name,
            checked_at=checked_at,
            command_run_id=command_run_id,
            output_dir=output_dir,
        )
        next_action_commands = [
            str(command)
            for command in template.get("next_action_commands", [])
        ]
        guarded_next_action_commands = [
            str(command)
            for command in template.get("guarded_next_action_commands", [])
        ]

    return {
        "status": state,
        "state": state,
        "checked_at": checked_at,
        "evidence_ref": "operator-input-readiness.json",
        "next_action": _provider_proof_operator_input_next_action(
            proof_name,
            state,
            fallback="inspect_operator_input_readiness",
            blocked_fields=blocked_fields,
        ),
        "effective_fail_on_blocked_exit_code": (
            _provider_proof_operator_input_effective_fail_exit_code(state)
        ),
        "issue_codes": issue_codes,
        "field_groups": field_groups,
        "field_contracts": field_contracts,
        "field_ownership": field_ownership,
        "field_statuses": field_statuses,
        "next_action_commands": next_action_commands,
        "guarded_next_action_commands": guarded_next_action_commands,
        "blocked_fields": blocked_fields,
        "required_fields": required_fields,
        "configured_fields": configured_fields,
        "required_evidence_after_unblock": (
            _provider_proof_operator_input_required_evidence(proof_name)
        ),
    }


def _provider_proof_operator_packet_payload(
    proof_name: str,
    command_run_id: str,
    output_dir: Path,
    proof_schema: Mapping[str, object],
    *,
    checked_at: str,
    operator_input_readiness: Mapping[str, object] | None = None,
) -> dict[str, object]:
    raw_required_fields = proof_schema.get("required_fields", [])
    required_fields = (
        [str(field) for field in raw_required_fields]
        if isinstance(raw_required_fields, list)
        else []
    )
    packet_operator_input_readiness = (
        operator_input_readiness
        or _provider_proof_operator_input_template_readiness(
            proof_name,
            checked_at=checked_at,
            command_run_id=command_run_id,
            output_dir=output_dir,
        )
    )
    return {
        "proof_id": proof_name,
        **_provider_proof_operator_packet_readme_contract(proof_name),
        "current_matrix_packet": "current-blocker-matrix.json",
        "current_matrix_packet_ref": str(
            Path(_provider_proof_command_path_text(output_dir))
            / "current-blocker-matrix.json"
        ),
        "current_matrix_packet_command": _proof_current_blocker_matrix_capture_command(
            command_run_id,
            output_dir,
        ),
        "current_matrix_operator_packet_ref": (
            f"/operator_proof_packets/{proof_name}"
        ),
        "source_artifacts": {
            "proof_plan": "proof-plan.json",
            "current_blocker_matrix": "current-blocker-matrix.json",
        },
        "operator_input_readiness": packet_operator_input_readiness,
        "proof_capture_commands_after_unblock": (
            _provider_proof_capture_commands_after_unblock(
                proof_name,
                command_run_id,
                output_dir,
            )
        ),
        "proof_record_schema": dict(proof_schema),
        "proof_record_required_fields": required_fields,
    }


def _provider_proof_operator_packet_markdown_section(packet: object) -> list[str]:
    if not isinstance(packet, Mapping):
        return []

    def scalar_line(field: str) -> str:
        return f"- {field}: `{packet.get(field, 'unknown')}`"

    def optional_scalar_lines(*fields: str) -> list[str]:
        return [
            f"- {field}: `{packet[field]}`"
            for field in fields
            if field in packet
        ]

    def list_lines(field: str) -> list[str]:
        raw_items = packet.get(field)
        if not isinstance(raw_items, list) or not raw_items:
            return [f"- {field}:", "  - `none`"]
        return [f"- {field}:", *[f"  - `{item}`" for item in raw_items]]

    def optional_list_lines(field: str) -> list[str]:
        return list_lines(field) if field in packet else []

    def mapping_lines(field: str) -> list[str]:
        raw_items = packet.get(field)
        if not isinstance(raw_items, Mapping) or not raw_items:
            return [f"- {field}:", "  - `none`"]
        lines = [f"- {field}:"]
        for key, value in raw_items.items():
            if isinstance(value, list) and str(key).endswith("_commands"):
                lines.append(f"  - {key}:")
                if value:
                    lines.extend(f"    - `{item}`" for item in value)
                else:
                    lines.append("    - `none`")
                continue
            lines.append(f"  - {key}: `{value}`")
        return lines

    def optional_mapping_lines(field: str) -> list[str]:
        return mapping_lines(field) if field in packet else []

    def operator_input_readiness_lines() -> list[str]:
        raw_readiness = packet.get("operator_input_readiness")
        if not isinstance(raw_readiness, Mapping):
            return []
        lines = ["- operator_input_readiness:"]
        for key, value in raw_readiness.items():
            if key == "field_ownership":
                lines.append("  - field_ownership:")
                if not isinstance(value, Mapping) or not value:
                    lines.append("    - `none`")
                    continue
                for field, raw_ownership in value.items():
                    lines.append(f"    - {field}:")
                    if not isinstance(raw_ownership, Mapping) or not raw_ownership:
                        lines.append(f"      - proof_id: `{raw_ownership}`")
                        continue
                    for ownership_key, ownership_value in raw_ownership.items():
                        lines.append(
                            f"      - {ownership_key}: `{ownership_value}`"
                        )
                continue
            if key == "field_statuses":
                lines.append("  - field_statuses:")
                if not isinstance(value, Mapping) or not value:
                    lines.append("    - `none`")
                    continue
                for field, raw_status in value.items():
                    lines.append(f"    - {field}:")
                    if not isinstance(raw_status, Mapping) or not raw_status:
                        lines.append(f"      - state: `{raw_status}`")
                        continue
                    for status_key, status_value in raw_status.items():
                        label = (
                            _provider_proof_operator_input_field_status_markdown_key(
                                str(status_key)
                            )
                        )
                        lines.append(f"      - {label}: `{status_value}`")
                continue
            if isinstance(value, list):
                lines.append(f"  - {key}:")
                if not value:
                    lines.append("    - `none`")
                    continue
                lines.extend(f"    - `{item}`" for item in value)
                continue
            if isinstance(value, Mapping):
                lines.append(f"  - {key}:")
                if not value:
                    lines.append("    - `none`")
                    continue
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, list):
                        lines.append(f"    - {nested_key}:")
                        if nested_value:
                            lines.extend(
                                f"      - `{item}`"
                                for item in nested_value
                            )
                        else:
                            lines.append("      - `none`")
                        continue
                    lines.append(f"    - {nested_key}: `{nested_value}`")
                continue
            lines.append(f"  - {key}: `{value}`")
        return lines

    return [
        "operator_proof_packet:",
        "",
        scalar_line("label"),
        scalar_line("packet_schema_version"),
        scalar_line("handoff_contract"),
        scalar_line("state_change_allowed"),
        scalar_line("state_change_guardrail"),
        scalar_line("secret_handling"),
        *mapping_lines("source_artifacts"),
        *optional_scalar_lines(
            "proof_id",
            "matrix_parity_ref",
            "proof_capture_matrix_ref",
            "proof_plan_packet",
            "proof_plan_packet_ref",
            "proof_plan_packet_command",
        "proof_plan_operator_packet_ref",
        "current_matrix_packet",
        "current_matrix_packet_ref",
        "current_matrix_packet_command",
        "current_matrix_operator_packet_ref",
        "current_gate_recovery_authority",
        "completion_evidence_ref",
    ),
        *optional_mapping_lines("current_state_packets"),
        *optional_mapping_lines("current_state_packet_commands"),
        *optional_mapping_lines("operator_input_field_contracts"),
        *operator_input_readiness_lines(),
        *list_lines("closure_evidence_refs"),
        *optional_mapping_lines("current_gate"),
        *list_lines("proof_capture_commands_after_unblock"),
        *optional_mapping_lines("proof_record_schema"),
        *optional_list_lines("proof_record_required_fields"),
        scalar_line("next_status_packet"),
        scalar_line("next_operator_packet"),
        *list_lines("must_capture"),
        *list_lines("store_in"),
        "",
    ]


def _provider_proof_current_status_markdown(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> str:
    matrix = _provider_proof_current_blocker_matrix_payload(
        args,
        env_values=env_values,
    )
    output_dir = getattr(args, "output_dir", None)
    if output_dir is None:
        output_dir = Path(f"social_media_optimiser/output/provider-proof/{args.run_id}")
    output_dir = Path(output_dir)
    base = _provider_proof_command_path_text(output_dir)
    run_id = str(args.run_id)
    checked_at = str(matrix.get("checked_at", "unknown"))
    completion = matrix.get("completion", {})
    closure = matrix.get("closure", {})
    operator_input_readiness = matrix.get("operator_input_readiness", {})
    proofs = matrix.get("proofs", {})
    operator_proof_packets = matrix.get("operator_proof_packets", {})
    if not isinstance(completion, Mapping):
        completion = {}
    if not isinstance(closure, Mapping):
        closure = {}
    if not isinstance(operator_input_readiness, Mapping):
        operator_input_readiness = {}
    if not isinstance(proofs, Mapping):
        proofs = {}
    if not isinstance(operator_proof_packets, Mapping):
        operator_proof_packets = {}

    def bullet_values(values: object, *, indent: str = "- ") -> list[str]:
        if not isinstance(values, list) or not values:
            return [f"{indent}`none`"]
        return [f"{indent}`{value}`" for value in values]

    def operator_field_group_lines(
        groups: object,
        *,
        group_indent: str = "- ",
        field_indent: str = "  - ",
    ) -> list[str]:
        if not isinstance(groups, Mapping) or not groups:
            return [f"{group_indent}`none`"]
        lines: list[str] = []
        for group_name, fields in groups.items():
            lines.append(f"{group_indent}{group_name}:")
            lines.extend(bullet_values(fields, indent=field_indent))
        return lines

    def operator_field_contract_lines(
        contracts: object,
        *,
        indent: str = "- ",
    ) -> list[str]:
        if not isinstance(contracts, Mapping) or not contracts:
            return [f"{indent}`none`"]
        return [
            f"{indent}{field}: `{contract}`"
            for field, contract in contracts.items()
        ]

    def operator_field_ownership_lines(
        ownership: object,
        *,
        field_indent: str = "- ",
        ownership_indent: str = "  - ",
    ) -> list[str]:
        if not isinstance(ownership, Mapping) or not ownership:
            return [f"{field_indent}`none`"]
        lines: list[str] = []
        for field, raw_ownership in ownership.items():
            lines.append(f"{field_indent}{field}:")
            if not isinstance(raw_ownership, Mapping) or not raw_ownership:
                lines.append(f"{ownership_indent}proof_id: `{raw_ownership}`")
                continue
            for ownership_key, ownership_value in raw_ownership.items():
                lines.append(f"{ownership_indent}{ownership_key}: `{ownership_value}`")
        return lines

    def operator_field_status_lines(
        statuses: object,
        *,
        field_indent: str = "- ",
        status_indent: str = "  - ",
    ) -> list[str]:
        if not isinstance(statuses, Mapping) or not statuses:
            return [f"{field_indent}`none`"]
        lines: list[str] = []
        for field, raw_status in statuses.items():
            lines.append(f"{field_indent}{field}:")
            if not isinstance(raw_status, Mapping) or not raw_status:
                lines.append(f"{status_indent}state: `{raw_status}`")
                continue
            for status_key, status_value in raw_status.items():
                label = _provider_proof_operator_input_field_status_markdown_key(
                    str(status_key)
                )
                lines.append(f"{status_indent}{label}: `{status_value}`")
        return lines

    def proof_lines(proof_id: str, title: str) -> list[str]:
        raw_proof = proofs.get(proof_id, {})
        proof = raw_proof if isinstance(raw_proof, Mapping) else {}
        blockers = proof.get("remaining_blockers")
        blocker_lines: list[str] = []
        if isinstance(blockers, list) and blockers:
            for raw_blocker in blockers:
                if not isinstance(raw_blocker, Mapping):
                    continue
                blocker_id = raw_blocker.get("blocker_id", "unknown")
                blocker_status = raw_blocker.get("status", "unknown")
                blocker_lines.extend(
                    [
                        f"- blocker: `{blocker_id}` (`{blocker_status}`)",
                        "  - missing inputs:",
                        *bullet_values(
                            raw_blocker.get("missing_inputs"),
                            indent="    - ",
                        ),
                    ]
                )
                issue_codes = raw_blocker.get("issue_codes")
                if isinstance(issue_codes, list) and issue_codes:
                    blocker_lines.extend(
                        [
                            "  - issue codes:",
                            *bullet_values(issue_codes, indent="    - "),
                        ]
                    )
        else:
            blocker_lines.append("- remaining blockers: `none`")

        proof_capture_command_lines: list[str] = []
        raw_capture_commands = proof.get("proof_capture_commands_after_unblock")
        if isinstance(raw_capture_commands, list) and raw_capture_commands:
            proof_capture_command_lines = [
                "proof_capture_commands_after_unblock:",
                "",
                *bullet_values(raw_capture_commands),
                "",
            ]
        proof_packet = operator_proof_packets.get(proof_id, {})
        if not isinstance(proof_packet, Mapping):
            proof_packet = {}
        proof_schema = proof_packet.get("proof_record_schema")
        proof_schema_lines: list[str] = []
        if isinstance(proof_schema, Mapping):
            proof_schema_lines = [
                "proof_record_schema:",
                "",
                f"- artifact_type: `{proof_schema.get('artifact_type', 'unknown')}`",
                "- allowed_outcomes:",
                *bullet_values(proof_schema.get("allowed_outcomes"), indent="  - "),
                f"- state_field: `{proof_schema.get('state_field', 'unknown')}`",
                "",
            ]
        proof_required_field_lines = [
            "proof_record_required_fields:",
            "",
            *bullet_values(proof_packet.get("proof_record_required_fields")),
            "",
        ]

        return [
            f"## {title}",
            "",
            f"- `{proof_id}`: `{proof.get('current_state', 'unknown')}`",
            f"- latest_record_outcome: `{proof.get('latest_record_outcome', 'unknown')}`",
            (
                "- accepted_record_available: "
                f"`{proof.get('accepted_record_available') is True}`"
            ),
            "",
            "Already-evidenced local items that must not be reopened:",
            "",
            *bullet_values(proof.get("do_not_reopen_as_blockers")),
            "",
            "Remaining blockers:",
            "",
            *blocker_lines,
            "",
            "Evidence refs:",
            "",
            *bullet_values(proof.get("evidence_refs")),
            "",
            *_provider_proof_operator_packet_markdown_section(proof_packet),
            *proof_schema_lines,
            *proof_required_field_lines,
            *proof_capture_command_lines,
        ]

    raw_operator_proofs = operator_input_readiness.get("proofs")
    operator_proof_lines: list[str] = []
    if isinstance(raw_operator_proofs, Mapping):
        for proof_id in [
            "provider-backed-live-voice-proof",
            "external-publication-proof",
        ]:
            raw_proof = raw_operator_proofs.get(proof_id)
            if not isinstance(raw_proof, Mapping):
                continue
            raw_field_groups = raw_proof.get("field_groups")
            field_group_lines: list[str] = []
            if isinstance(raw_field_groups, Mapping):
                for group_name, fields in raw_field_groups.items():
                    field_group_lines.extend(
                        [
                            f"    - {group_name}:",
                            *bullet_values(fields, indent="      - "),
                        ]
                    )
            operator_proof_lines.extend(
                [
                    f"- `{proof_id}`: `{raw_proof.get('state', 'unknown')}`",
                    f"  - next_action: `{raw_proof.get('next_action', 'unknown')}`",
                    "  - blocked fields:",
                    *bullet_values(raw_proof.get("blocked_fields"), indent="    - "),
                    "  - required fields:",
                    *bullet_values(raw_proof.get("required_fields"), indent="    - "),
                    "  - configured fields:",
                    *bullet_values(
                        raw_proof.get("configured_fields"),
                        indent="    - ",
                    ),
                    "  - field_contracts:",
                    *operator_field_contract_lines(
                        raw_proof.get("field_contracts"),
                        indent="    - ",
                    ),
                    "  - field_ownership:",
                    *operator_field_ownership_lines(
                        raw_proof.get("field_ownership"),
                        field_indent="    - ",
                        ownership_indent="      - ",
                    ),
                    "  - field_statuses:",
                    *operator_field_status_lines(
                        raw_proof.get("field_statuses"),
                        field_indent="    - ",
                        status_indent="      - ",
                    ),
                    "  - issue_codes:",
                    *bullet_values(raw_proof.get("issue_codes"), indent="    - "),
                    "  - field_groups:",
                    *field_group_lines,
                    "  - next_action_commands:",
                    *bullet_values(
                        raw_proof.get("next_action_commands"),
                        indent="    - ",
                    ),
                    "  - guarded_next_action_commands:",
                    *bullet_values(
                        raw_proof.get("guarded_next_action_commands"),
                        indent="    - ",
                    ),
                    "  - required evidence after unblock:",
                    *bullet_values(
                        raw_proof.get("required_evidence_after_unblock"),
                        indent="    - ",
                    ),
                ]
            )

    current_state_packets = matrix.get("current_state_packets", {})
    if not isinstance(current_state_packets, Mapping):
        current_state_packets = {}
    current_state_packet_commands = matrix.get("current_state_packet_commands", {})
    if not isinstance(current_state_packet_commands, Mapping):
        current_state_packet_commands = {}
    completion_issue_codes = bullet_values(completion.get("issue_codes"), indent="  - ")
    latest_failed_proofs = bullet_values(
        completion.get("latest_failed_proofs"),
        indent="  - ",
    )
    missing_accepted_proofs = bullet_values(
        completion.get("missing_accepted_proofs"),
        indent="  - ",
    )

    lines = [
        "# Current Proof Status",
        "",
        f"- checked_at: {checked_at}",
        f"- run_id: `{run_id}`",
        (
            "- generator: `"
            f"{_proof_current_status_command(run_id, output_dir)}`"
        ),
        (
            "- boundary: no secret values, no raw provider responses, no "
            "private audio, no blocker-state change"
        ),
        "",
        "This status packet is generated from the current blocker matrix and proof workspace artifacts. It is a no-secret operator summary, not accepted proof.",
        "",
        "## Current Gate",
        "",
        f"- `completion-status.json`: `{completion.get('status', 'unknown')}`",
        (
            "- completion evidence ref: "
            f"`{completion.get('evidence_ref', 'completion-status.json')}`"
        ),
        (
            "- `closure-review-template.json`: "
            f"`{closure.get('closure_review_template_status', 'unknown')}`"
        ),
        (
            "- `closure-review-status.json`: "
            f"`{closure.get('closure_review_status', 'unknown')}`"
        ),
        (
            "- `blocker-state-update.json`: "
            f"`{closure.get('blocker_state_update_status', 'unknown')}`"
        ),
        (
            "- state_change_allowed: "
            f"`{closure.get('state_change_allowed') is True}`"
        ),
        (
            "- goal_completion_claimed: "
            f"`{closure.get('goal_completion_claimed') is True}`"
        ),
        "- closure evidence refs:",
        *bullet_values(closure.get("evidence_refs"), indent="  - "),
        "- completion issue codes:",
        *completion_issue_codes,
        "- latest failed proofs:",
        *latest_failed_proofs,
        "- missing accepted proofs:",
        *missing_accepted_proofs,
        f"- completion next_action: `{completion.get('next_action', 'unknown')}`",
        "- completion next_action_commands:",
        *bullet_values(completion.get("next_action_commands"), indent="  - "),
        "",
        "## Current State Packet Contract",
        "",
        "- current_state_packets:",
        *[
            f"  - {key}: `{value}`"
            for key, value in current_state_packets.items()
        ],
        f"- next_status_packet: `{matrix.get('next_status_packet', 'unknown')}`",
        f"- next_operator_packet: `{matrix.get('next_operator_packet', 'unknown')}`",
        "- current_state_packet_commands:",
        *[
            f"  - {key}: `{value}`"
            for key, value in current_state_packet_commands.items()
        ],
        "",
        *proof_lines("provider-backed-live-voice-proof", "Provider-Backed Live Voice"),
        *proof_lines("external-publication-proof", "External Publication"),
        "## Operator Input Readiness",
        "",
        f"- status: `{operator_input_readiness.get('status', 'unknown')}`",
        f"- checked_at: `{operator_input_readiness.get('checked_at', 'unknown')}`",
        (
            "- effective `--fail-on-blocked` exit code: "
            f"`{operator_input_readiness.get('effective_fail_on_blocked_exit_code', 'unknown')}`"
        ),
        (
            "- strict readiness command: "
            f"`{operator_input_readiness.get('strict_readiness_command', 'unknown')}`"
        ),
        "- next_action_commands:",
        *bullet_values(
            operator_input_readiness.get("next_action_commands"),
            indent="  - ",
        ),
        "- guarded_next_action_commands:",
        *bullet_values(
            operator_input_readiness.get("guarded_next_action_commands"),
            indent="  - ",
        ),
        "",
        "Issue codes:",
        "",
        *bullet_values(operator_input_readiness.get("issue_codes")),
        "",
        "Blocked fields:",
        "",
        *bullet_values(operator_input_readiness.get("blocked_fields")),
        "",
        "Required fields:",
        "",
        *bullet_values(operator_input_readiness.get("required_fields")),
        "",
        "Configured fields:",
        "",
        *bullet_values(operator_input_readiness.get("configured_fields")),
        "",
        "Field contracts:",
        "",
        *operator_field_contract_lines(operator_input_readiness.get("field_contracts")),
        "",
        "Field ownership:",
        "",
        *operator_field_ownership_lines(
            operator_input_readiness.get("field_ownership")
        ),
        "",
        "Field groups:",
        "",
        *operator_field_group_lines(operator_input_readiness.get("field_groups")),
        "",
        "Field statuses:",
        "",
        *operator_field_status_lines(operator_input_readiness.get("field_statuses")),
        "",
        "Per-proof readiness:",
        "",
        *operator_proof_lines,
        "",
        "## Regeneration Commands",
        "",
        "Run these from the repository root after operator inputs or proof artifacts change:",
        "",
        "```sh",
        _proof_current_blocker_matrix_capture_command(run_id, output_dir),
        _proof_current_status_capture_command(run_id, output_dir),
        _proof_operator_unblocker_checklist_capture_command(run_id, output_dir),
        "```",
        "",
        "## Next Packets",
        "",
        f"- `{base}/current-blocker-matrix.json`",
        f"- `{base}/current-proof-status.md`",
        f"- `{base}/operator-unblocker-checklist.md`",
        "",
        "Do not run closure review or blocker-state update as evidence of completion while the latest proof records remain failed.",
    ]
    return "\n".join(lines) + "\n"


def _print_provider_proof_current_status(args: argparse.Namespace) -> None:
    print(_provider_proof_current_status_markdown(args), end="")


def _provider_proof_command_path_text(path: Path | str) -> str:
    raw_path = Path(path)
    try:
        return raw_path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except (OSError, RuntimeError, ValueError):
        return _provider_proof_output_path_text(raw_path)


def _provider_proof_backticked_items(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    return [f"`{item}`" for item in items]


def _provider_proof_operator_unblocker_checklist_markdown(
    args: argparse.Namespace,
    *,
    env_values: dict[str, str | None] | None = None,
) -> str:
    matrix = _provider_proof_current_blocker_matrix_payload(
        args,
        env_values=env_values,
    )
    output_dir = getattr(args, "output_dir", None)
    if output_dir is None:
        output_dir = Path(f"social_media_optimiser/output/provider-proof/{args.run_id}")
    output_dir = Path(output_dir)
    base = _provider_proof_command_path_text(output_dir)
    run_id = str(args.run_id)
    checked_at = str(matrix["checked_at"])
    completion = matrix["completion"]
    closure = matrix["closure"]
    proofs = matrix["proofs"]
    operator_proof_packets = matrix.get("operator_proof_packets", {})
    if not isinstance(completion, Mapping):
        completion = {}
    if not isinstance(closure, Mapping):
        closure = {}
    if not isinstance(proofs, Mapping):
        proofs = {}
    if not isinstance(operator_proof_packets, Mapping):
        operator_proof_packets = {}
    voice = proofs.get("provider-backed-live-voice-proof", {})
    publication = proofs.get("external-publication-proof", {})
    if not isinstance(voice, Mapping):
        voice = {}
    if not isinstance(publication, Mapping):
        publication = {}
    voice_blockers = voice.get("remaining_blockers")
    publication_blockers = publication.get("remaining_blockers")
    voice_accepted = (
        voice.get("latest_record_outcome") == "accepted"
        and voice.get("accepted_record_available") is True
    )
    publication_accepted = (
        publication.get("latest_record_outcome") == "accepted"
        and publication.get("accepted_record_available") is True
    )
    voice_blocker = (
        voice_blockers[0]
        if isinstance(voice_blockers, list)
        and voice_blockers
        and isinstance(voice_blockers[0], Mapping)
        else {}
    )
    publication_blocker = (
        publication_blockers[0]
        if isinstance(publication_blockers, list)
        and publication_blockers
        and isinstance(publication_blockers[0], Mapping)
        else {}
    )
    voice_inputs = _provider_proof_backticked_items(
        voice_blocker.get("missing_inputs")
    )
    publication_inputs = _provider_proof_backticked_items(
        publication_blocker.get("missing_inputs")
    )
    voice_blocker_status = str(voice_blocker.get("status") or "unknown")
    publication_blocker_status = str(publication_blocker.get("status") or "unknown")
    if not voice_inputs and not voice_accepted:
        voice_blocker_status = "ready_for_record_capture"
    if not publication_inputs and not publication_accepted:
        publication_inputs = [
            "`LINKEDIN_ACCESS_TOKEN or LINKEDIN_ACCESS_TOKEN_FILE`",
            "`LinkedIn policy and account-permission acknowledgement`",
            "`durable external destination URL or platform id`",
            "`rollback or postcondition evidence`",
        ]
    proof_level_blockers_remain = bool(voice_inputs or publication_inputs)
    completion_issue_codes = _provider_proof_backticked_items(
        completion.get("issue_codes")
    )
    if not completion_issue_codes:
        completion_issue_codes = ["`none`"]
    latest_failed_proofs = _provider_proof_backticked_items(
        completion.get("latest_failed_proofs")
    )
    if not latest_failed_proofs:
        latest_failed_proofs = ["`none`"]
    missing_accepted_proofs = _provider_proof_backticked_items(
        completion.get("missing_accepted_proofs")
    )
    if not missing_accepted_proofs:
        missing_accepted_proofs = ["`none`"]
    closure_evidence_refs = _provider_proof_backticked_items(
        closure.get("evidence_refs")
    )
    if not closure_evidence_refs:
        closure_evidence_refs = ["`none`"]
    operator_input_readiness = _provider_proof_json_object(
        output_dir / "operator-input-readiness.json"
    )

    def command_list(raw_commands: object) -> list[str]:
        if not isinstance(raw_commands, list):
            return []
        commands = [str(command) for command in raw_commands if str(command)]
        return commands if len(commands) == len(raw_commands) else []

    def indented_backticked_values(raw_values: object, *, indent: str) -> list[str]:
        if not isinstance(raw_values, list) or not raw_values:
            return [f"{indent}`none`"]
        return [f"{indent}`{value}`" for value in raw_values]

    def indented_field_contracts(raw_contracts: object, *, indent: str) -> list[str]:
        if not isinstance(raw_contracts, Mapping) or not raw_contracts:
            return [f"{indent}`none`"]
        return [
            f"{indent}- {field}: `{contract}`"
            for field, contract in raw_contracts.items()
        ]

    def indented_field_ownership(raw_ownership: object, *, indent: str) -> list[str]:
        if not isinstance(raw_ownership, Mapping) or not raw_ownership:
            return [f"{indent}`none`"]
        lines: list[str] = []
        for field, ownership in raw_ownership.items():
            lines.append(f"{indent}- {field}:")
            if not isinstance(ownership, Mapping) or not ownership:
                lines.append(f"{indent}  - proof_id: `{ownership}`")
                continue
            for ownership_key, ownership_value in ownership.items():
                lines.append(f"{indent}  - {ownership_key}: `{ownership_value}`")
        return lines

    def indented_field_statuses(raw_statuses: object, *, indent: str) -> list[str]:
        if not isinstance(raw_statuses, Mapping) or not raw_statuses:
            return [f"{indent}`none`"]
        lines: list[str] = []
        for field, raw_status in raw_statuses.items():
            lines.append(f"{indent}- {field}:")
            if not isinstance(raw_status, Mapping) or not raw_status:
                lines.append(f"{indent}  - state: `{raw_status}`")
                continue
            for status_key, status_value in raw_status.items():
                label = _provider_proof_operator_input_field_status_markdown_key(
                    str(status_key)
                )
                lines.append(f"{indent}  - {label}: `{status_value}`")
        return lines

    def proof_capture_command_section(proof: Mapping[str, object]) -> list[str]:
        commands = command_list(proof.get("proof_capture_commands_after_unblock"))
        if not commands:
            return []
        return [
            "proof_capture_commands_after_unblock:",
            "",
            "```sh",
            *commands,
            "```",
            "",
        ]

    def proof_record_required_fields_section(proof_id: str) -> list[str]:
        raw_packet = operator_proof_packets.get(proof_id)
        if not isinstance(raw_packet, Mapping):
            return []
        raw_fields = raw_packet.get("proof_record_required_fields")
        if not isinstance(raw_fields, list) or not raw_fields:
            return []
        return [
            "proof_record_required_fields:",
            "",
            *[f"- `{field}`" for field in raw_fields],
            "",
        ]

    def proof_record_schema_section(proof_id: str) -> list[str]:
        raw_packet = operator_proof_packets.get(proof_id)
        if not isinstance(raw_packet, Mapping):
            return []
        raw_schema = raw_packet.get("proof_record_schema")
        if not isinstance(raw_schema, Mapping):
            return []
        raw_outcomes = raw_schema.get("allowed_outcomes")
        outcome_lines = (
            [f"  - `{outcome}`" for outcome in raw_outcomes]
            if isinstance(raw_outcomes, list) and raw_outcomes
            else ["  - `none`"]
        )
        return [
            "proof_record_schema:",
            "",
            f"- artifact_type: `{raw_schema.get('artifact_type', 'unknown')}`",
            "- allowed_outcomes:",
            *outcome_lines,
            f"- state_field: `{raw_schema.get('state_field', 'unknown')}`",
            "",
        ]

    operator_input_command_path = _provider_proof_operator_input_command_path(
        operator_input_readiness,
        output_dir,
    )
    operator_input_retry_commands = command_list(
        operator_input_readiness.get("next_action_commands")
    ) or _proof_operator_input_retry_commands_for_input(
        run_id,
        operator_input_command_path,
    )
    guarded_operator_input_retry_commands = command_list(
        operator_input_readiness.get("guarded_next_action_commands")
    ) or _proof_operator_input_retry_commands_for_input(
        run_id,
        operator_input_command_path,
        fail_on_blocked=True,
    )

    def proof_label_text(labels: list[str]) -> str:
        if len(labels) == 2:
            return f"{labels[0]} and {labels[1]}"
        if labels:
            return labels[0]
        return "none"

    failed_record_labels: list[str] = []
    if voice.get("latest_record_outcome") == "failed":
        failed_record_labels.append("provider-backed live voice")
    if publication.get("latest_record_outcome") == "failed":
        failed_record_labels.append("external publication")

    incomplete_coverage_labels: list[str] = []
    if voice.get("current_state") == "accepted_record_missing_from_some_targets":
        incomplete_coverage_labels.append("provider-backed live voice")
    if publication.get("current_state") == "accepted_record_missing_from_some_targets":
        incomplete_coverage_labels.append("external publication")

    invalid_note_labels: list[str] = []
    if voice.get("current_state") == "latest_record_has_invalid_fields":
        invalid_note_labels.append("provider-backed live voice")
    if publication.get("current_state") == "latest_record_has_invalid_fields":
        invalid_note_labels.append("external publication")

    secret_note_labels: list[str] = []
    if voice.get("current_state") == "latest_record_contains_secret_shape":
        secret_note_labels.append("provider-backed live voice")
    if publication.get("current_state") == "latest_record_contains_secret_shape":
        secret_note_labels.append("external publication")

    missing_record_labels: list[str] = []
    if (
        not voice_accepted
        and "provider-backed live voice" not in failed_record_labels
        and "provider-backed live voice" not in incomplete_coverage_labels
        and "provider-backed live voice" not in invalid_note_labels
        and "provider-backed live voice" not in secret_note_labels
    ):
        missing_record_labels.append("provider-backed live voice")
    if (
        not publication_accepted
        and "external publication" not in failed_record_labels
        and "external publication" not in incomplete_coverage_labels
        and "external publication" not in invalid_note_labels
        and "external publication" not in secret_note_labels
    ):
        missing_record_labels.append("external publication")

    if secret_note_labels:
        accepted_proof_state = (
            "blocked by secret-shaped accepted audit notes for "
            f"{proof_label_text(secret_note_labels)}"
        )
    elif invalid_note_labels:
        accepted_proof_state = (
            "blocked by invalid accepted audit notes for "
            f"{proof_label_text(invalid_note_labels)}"
        )
    elif failed_record_labels:
        accepted_proof_state = (
            "blocked by latest failed records for "
            f"{proof_label_text(failed_record_labels)}"
        )
    elif incomplete_coverage_labels:
        accepted_proof_state = (
            "blocked by incomplete accepted-record audit coverage for "
            f"{proof_label_text(incomplete_coverage_labels)}"
        )
    elif missing_record_labels:
        accepted_proof_state = (
            f"missing accepted records for {proof_label_text(missing_record_labels)}"
        )
    else:
        accepted_proof_state = "all required accepted records are available"

    current_credential_snapshot_lines: list[str] = []
    credential_snapshot = _provider_proof_json_object(
        output_dir / "credential-snapshot.json"
    )
    raw_snapshots = credential_snapshot.get("snapshots")
    if isinstance(raw_snapshots, Mapping):
        snapshot_state_lines: list[str] = []
        raw_checked_at = credential_snapshot.get("checked_at")
        snapshot_checked_at_line = (
            f"- snapshot checked_at: `{raw_checked_at}`"
            if isinstance(raw_checked_at, str) and raw_checked_at
            else "- snapshot checked_at: `unknown`"
        )
        for proof_name in [
            "provider-backed-live-voice-proof",
            "external-publication-proof",
        ]:
            raw_snapshot = raw_snapshots.get(proof_name)
            if not isinstance(raw_snapshot, Mapping):
                continue
            raw_state = raw_snapshot.get("state")
            if isinstance(raw_state, str) and raw_state:
                snapshot_state_lines.append(f"- `{proof_name}`: `{raw_state}`")
        if snapshot_state_lines:
            current_credential_snapshot_lines = [
                "Current snapshot state:",
                "",
                snapshot_checked_at_line,
                *snapshot_state_lines,
                "",
            ]

    credential_snapshot_section = (
        [
            "## Credential Snapshot",
            "",
            (
                "After supplying or changing provider/platform inputs, refresh "
                "the no-secret credential state before rerunning proof preflights:"
            ),
            "",
            "Expected snapshot state before retrying preflight:",
            "",
            (
                "- `provider-backed-live-voice-proof`: "
                "`runtime_configuration_present_unverified`"
            ),
            (
                "- `external-publication-proof`: "
                "`runtime_configuration_present_unverified`"
            ),
            "",
            *current_credential_snapshot_lines,
            "",
            "```sh",
            *operator_input_retry_commands[1:3],
            "```",
            "",
        ]
        if proof_level_blockers_remain
        else []
    )

    operator_inputs_section: list[str] = []
    operator_inputs_template_path = output_dir / "operator-inputs.template.env"
    if proof_level_blockers_remain and operator_inputs_template_path.exists():
        current_operator_input_lines: list[str] = []
        raw_input_status = operator_input_readiness.get("status")
        raw_input_checked_at = operator_input_readiness.get("checked_at")
        raw_input_effective_exit_code = operator_input_readiness.get(
            "effective_fail_on_blocked_exit_code"
        )
        raw_input_issue_codes = operator_input_readiness.get("issue_codes")
        raw_input_issues = operator_input_readiness.get("issues")
        if isinstance(raw_input_status, str) and raw_input_status:
            effective_exit_code = (
                raw_input_effective_exit_code
                if isinstance(raw_input_effective_exit_code, int)
                else _provider_proof_operator_input_effective_fail_exit_code(
                    raw_input_status
                )
            )
            current_operator_input_lines = [
                "Current operator input readiness:",
                "",
                (
                    f"- input readiness checked_at: `{raw_input_checked_at}`"
                    if isinstance(raw_input_checked_at, str) and raw_input_checked_at
                    else "- input readiness checked_at: `unknown`"
                ),
                f"- input readiness status: `{raw_input_status}`",
                (
                    "- input readiness `--fail-on-blocked` exit code: "
                    f"`{effective_exit_code}`"
                ),
            ]
            if isinstance(raw_input_issue_codes, list) and raw_input_issue_codes:
                current_operator_input_lines.extend(
                    [
                        "- input readiness issue codes:",
                        *[f"  `{code}`" for code in raw_input_issue_codes],
                    ]
                )
            blocked_fields: list[str] = []
            if isinstance(raw_input_issues, list):
                for raw_issue in raw_input_issues:
                    if not isinstance(raw_issue, Mapping):
                        continue
                    raw_field = raw_issue.get("field")
                    if (
                        isinstance(raw_field, str)
                        and raw_field
                        and raw_field not in blocked_fields
                    ):
                        blocked_fields.append(raw_field)
            if blocked_fields:
                current_operator_input_lines.extend(
                    [
                        "- input readiness blocked fields:",
                        *[f"  `{field}`" for field in blocked_fields],
                    ]
                )
            current_operator_input_lines.extend(
                [
                    "- input readiness required fields:",
                    *indented_backticked_values(
                        operator_input_readiness.get("required_fields"),
                        indent="  ",
                    ),
                    "- input readiness configured fields:",
                    *indented_backticked_values(
                        operator_input_readiness.get("configured_fields"),
                        indent="  ",
                    ),
                    "- input readiness field contracts:",
                    *indented_field_contracts(
                        operator_input_readiness.get("field_contracts"),
                        indent="  ",
                    ),
                    "- input readiness field ownership:",
                    *indented_field_ownership(
                        operator_input_readiness.get("field_ownership"),
                        indent="  ",
                    ),
                ]
            )
            raw_input_field_groups = operator_input_readiness.get("field_groups")
            if isinstance(raw_input_field_groups, Mapping):
                current_operator_input_lines.append("- input readiness field groups:")
                for group_name, raw_fields in raw_input_field_groups.items():
                    current_operator_input_lines.append(f"  - {group_name}:")
                    current_operator_input_lines.extend(
                        indented_backticked_values(raw_fields, indent="    ")
                    )
            current_operator_input_lines.extend(
                [
                    "- input readiness field statuses:",
                    *indented_field_statuses(
                        operator_input_readiness.get("field_statuses"),
                        indent="  ",
                    ),
                ]
            )
            raw_input_proofs = operator_input_readiness.get("proofs")
            if isinstance(raw_input_proofs, Mapping):
                current_operator_input_lines.append("- per-proof input readiness:")
                for proof_name in [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ]:
                    raw_proof = raw_input_proofs.get(proof_name)
                    if not isinstance(raw_proof, Mapping):
                        continue
                    raw_state = raw_proof.get("state")
                    proof_state = raw_state if isinstance(raw_state, str) else "unknown"

                    def proof_fields(field_name: str) -> list[str]:
                        raw_fields = raw_proof.get(field_name, [])
                        if not isinstance(raw_fields, list):
                            return []
                        fields: list[str] = []
                        for raw_field in raw_fields:
                            field = str(raw_field)
                            if field and field not in fields:
                                fields.append(field)
                        return fields

                    proof_blocked_fields: list[str] = []
                    proof_field_groups = {
                        "missing fields": proof_fields("missing_fields"),
                        "placeholder fields": proof_fields("placeholder_fields"),
                        "invalid fields": proof_fields("invalid_fields"),
                        "unavailable secret-file fields": proof_fields(
                            "unavailable_secret_file_fields",
                        ),
                    }
                    for fields in proof_field_groups.values():
                        for field in fields:
                            if field not in proof_blocked_fields:
                                proof_blocked_fields.append(field)
                    proof_required_fields = proof_fields("required_fields")
                    proof_configured_fields = proof_fields("configured_fields")
                    proof_issue_codes: list[str] = []
                    if isinstance(raw_input_issues, list):
                        for raw_issue in raw_input_issues:
                            if not isinstance(raw_issue, Mapping):
                                continue
                            raw_field = raw_issue.get("field")
                            raw_code = raw_issue.get("code")
                            if not (
                                isinstance(raw_field, str)
                                and raw_field in proof_blocked_fields
                                and isinstance(raw_code, str)
                                and raw_code
                            ):
                                continue
                            if raw_code not in proof_issue_codes:
                                proof_issue_codes.append(raw_code)
                    current_operator_input_lines.append(
                        f"  - `{proof_name}`: `{proof_state}`"
                    )
                    proof_next_action = _provider_proof_operator_input_next_action(
                        proof_name,
                        proof_state,
                        fallback=str(
                            operator_input_readiness.get(
                                "next_action",
                                "inspect_operator_input_readiness",
                            )
                        ),
                        blocked_fields=proof_blocked_fields,
                    )
                    current_operator_input_lines.append(
                        f"    - {proof_name} next action: `{proof_next_action}`"
                    )
                    current_operator_input_lines.extend(
                        [
                            f"    - {proof_name} required fields:",
                            *(
                                [f"      `{field}`" for field in proof_required_fields]
                                or ["      `none`"]
                            ),
                            f"    - {proof_name} configured fields:",
                            *(
                                [
                                    f"      `{field}`"
                                    for field in proof_configured_fields
                                ]
                                or ["      `none`"]
                            ),
                            f"    - {proof_name} field contracts:",
                            *indented_field_contracts(
                                raw_proof.get("field_contracts"),
                                indent="      ",
                            ),
                            f"    - {proof_name} field ownership:",
                            *indented_field_ownership(
                                raw_proof.get("field_ownership"),
                                indent="      ",
                            ),
                            f"    - {proof_name} field statuses:",
                            *indented_field_statuses(
                                raw_proof.get("field_statuses"),
                                indent="      ",
                            ),
                        ]
                    )
                    for command_group_name in [
                        "next_action_commands",
                        "guarded_next_action_commands",
                    ]:
                        fallback_commands = (
                            guarded_operator_input_retry_commands
                            if command_group_name == "guarded_next_action_commands"
                            else operator_input_retry_commands
                        )
                        raw_commands = raw_proof.get(
                            command_group_name,
                            fallback_commands,
                        )
                        if not isinstance(raw_commands, list):
                            raw_commands = fallback_commands
                        commands = [
                            str(command)
                            for command in raw_commands
                            if str(command)
                        ]
                        if not commands:
                            continue
                        current_operator_input_lines.extend(
                            [
                                f"    - {proof_name} {command_group_name}:",
                                *[f"      `{command}`" for command in commands],
                            ]
                        )
                    current_operator_input_lines.extend(
                        [
                            (
                                f"    - {proof_name} required evidence after "
                                "unblock:"
                            ),
                            *[
                                f"      `{evidence}`"
                                for evidence in (
                                    _provider_proof_operator_input_required_evidence(
                                        proof_name
                                    )
                                )
                            ],
                        ]
                    )
                    if proof_issue_codes:
                        current_operator_input_lines.extend(
                            [
                                f"    - {proof_name} issue codes:",
                                *[f"      `{code}`" for code in proof_issue_codes],
                            ]
                        )
                    for group_label, fields in proof_field_groups.items():
                        if fields:
                            current_operator_input_lines.extend(
                                [
                                    f"    - {proof_name} {group_label}:",
                                    *[f"      `{field}`" for field in fields],
                                ]
                            )
            current_operator_input_lines.append("")
        operator_inputs_section = [
            "## Operator Input Template",
            "",
            (
                "Use the placeholder-only input template to collect the remaining "
                "external inputs before refreshing credential snapshot and preflight:"
            ),
            "",
            f"- `{base}/operator-inputs.template.env`",
            "",
            *current_operator_input_lines,
            "Validate the filled file without printing values before refreshing snapshots:",
            "",
            (
                "Automation can add `--fail-on-blocked` to make the readiness "
                "command exit nonzero after writing JSON when inputs are still blocked."
            ),
            "",
            "```sh",
            operator_input_retry_commands[0],
            "```",
            "",
            "Strict automation readiness gate:",
            "",
            "```sh",
            guarded_operator_input_retry_commands[0],
            "```",
            "",
            "Guarded retry sequence:",
            "",
            "```sh",
            *guarded_operator_input_retry_commands,
            "```",
            "",
        ]

    checkpoint_section: list[str] = []
    operator_checkpoint_path = output_dir / "operator-checkpoint.json"
    checkpoints_list_path = output_dir / "checkpoints.list.json"
    if operator_checkpoint_path.exists() or checkpoints_list_path.exists():
        checkpoint_kind = "unknown"
        checkpoint_id = "unknown"
        event_cursor = "unknown"
        operator_checkpoint = _provider_proof_json_object(operator_checkpoint_path)
        raw_checkpoint = operator_checkpoint.get("checkpoint")

        def capture_checkpoint_fields(raw_candidate: object) -> None:
            nonlocal checkpoint_id, checkpoint_kind, event_cursor
            if not isinstance(raw_candidate, Mapping):
                return
            raw_checkpoint_id = raw_candidate.get("checkpoint_id")
            if isinstance(raw_checkpoint_id, str) and raw_checkpoint_id:
                checkpoint_id = raw_checkpoint_id
            raw_checkpoint_kind = raw_candidate.get("checkpoint_kind")
            if isinstance(raw_checkpoint_kind, str) and raw_checkpoint_kind:
                checkpoint_kind = raw_checkpoint_kind
            raw_event_cursor = raw_candidate.get("event_cursor")
            if isinstance(raw_event_cursor, int | str):
                event_cursor = str(raw_event_cursor)

        if isinstance(raw_checkpoint, Mapping):
            capture_checkpoint_fields(raw_checkpoint)
        if checkpoint_kind == "unknown" or checkpoint_id == "unknown" or event_cursor == "unknown":
            checkpoints_list = _provider_proof_json_object(checkpoints_list_path)
            raw_checkpoints = checkpoints_list.get("checkpoints")
            if isinstance(raw_checkpoints, list) and raw_checkpoints:
                raw_first_checkpoint = raw_checkpoints[0]
                capture_checkpoint_fields(raw_first_checkpoint)
        checkpoint_section = [
            "## Checkpoint Evidence",
            "",
            (
                "Preserve the current long-running recovery checkpoint evidence "
                "while retrying external proof capture:"
            ),
            "",
        ]
        if operator_checkpoint_path.exists():
            checkpoint_section.append(f"- `{base}/operator-checkpoint.json`")
        if checkpoints_list_path.exists():
            checkpoint_section.append(f"- `{base}/checkpoints.list.json`")
        checkpoint_section.extend(
            [
                f"- checkpoint id: `{checkpoint_id}`",
                f"- checkpoint kind: `{checkpoint_kind}`",
                f"- event cursor: `{event_cursor}`",
                "",
            ]
        )

    voice_record_commands = [
        *_proof_record_template_commands("provider-backed-live-voice-proof", run_id),
        *_proof_record_next_commands(
            "provider-backed-live-voice-proof",
            run_id,
            preflight_validation_path=(
                f"{base}/provider-backed-live-voice-proof.preflight-validation.json"
            ),
            workspace_validation_path=f"{base}/workspace-validation.json",
        ),
    ]
    publication_record_commands = [
        *_proof_record_template_commands("external-publication-proof", run_id),
        *_proof_record_next_commands(
            "external-publication-proof",
            run_id,
            preflight_validation_path=(
                f"{base}/external-publication-proof.preflight-validation.json"
            ),
            workspace_validation_path=f"{base}/workspace-validation.json",
            ),
        ]

    def audit_note_repair_section(
        title: str,
        blocker: Mapping[str, object],
    ) -> list[str]:
        repair_inputs = _provider_proof_backticked_items(blocker.get("missing_inputs"))
        if not repair_inputs:
            repair_inputs = ["`valid accepted proof audit note fields`"]
        return [
            f"## {title}",
            "",
            "Accepted proof audit note needs repair.",
            "",
            "Operator must still supply:",
            "",
            *[f"- {item}" for item in repair_inputs],
            "",
            "Next action:",
            "",
            (
                "- record a corrected validated accepted proof record, then "
                "rerun `provider-proof-completion-status`."
            ),
        ]

    def audit_coverage_section(
        title: str,
        missing_targets: list[str],
    ) -> list[str]:
        return [
            f"## {title}",
            "",
            "Accepted proof audit coverage is incomplete.",
            "",
            "Missing audit targets:",
            "",
            *[f"- {target}" for target in missing_targets],
            "",
            "Next action:",
            "",
            (
                "- record the same validated accepted proof record into every "
                "missing audit target, then rerun `provider-proof-completion-status`."
            ),
        ]

    if voice_accepted:
        voice_section = [
            "## Provider-Backed Live Voice",
            "",
            "Accepted proof status:",
            "",
            "- Accepted proof record is available.",
            "- No proof-level operator inputs remain for this proof.",
        ]
    elif voice.get("current_state") in {
        "latest_record_contains_secret_shape",
        "latest_record_has_invalid_fields",
    }:
        voice_section = audit_note_repair_section(
            "Provider-Backed Live Voice",
            voice_blocker,
        )
    elif voice.get("current_state") == "accepted_record_missing_from_some_targets":
        voice_section = audit_coverage_section(
            "Provider-Backed Live Voice",
            voice_inputs,
        )
    else:
        voice_supply_lines = (
            [
                "Operator must still supply:",
                "",
                *[f"- {item}" for item in voice_inputs],
                "",
            ]
            if voice_inputs
            else [
                "No live-voice operator inputs remain; capture and record same-run proof evidence next.",
                "",
            ]
        )
        voice_preflight_intro = (
            "After those inputs are available, rerun:"
            if voice_inputs
            else "Before filling the accepted proof record, refresh the preflight evidence:"
        )
        voice_section = [
            "## Provider-Backed Live Voice",
            "",
            "Already ready in this workspace:",
            "",
            "- Product run preflight exists for the UUID run.",
            (
                "- Local LiveKit transport, LiveKit participant construction, "
                "local Kokoro, Rust voice edge, and context pruning are ready."
            ),
            (
                "- `openrouter-livekit` provider readiness is ready under local "
                "LiveKit dev input names."
            ),
            "",
            "Current blocker status:",
            "",
            f"- Current live voice blocker status: `{voice_blocker_status}`",
            "",
            *voice_supply_lines,
            *_provider_proof_operator_packet_markdown_section(
                operator_proof_packets.get("provider-backed-live-voice-proof")
            ),
            *proof_record_schema_section("provider-backed-live-voice-proof"),
            *proof_record_required_fields_section("provider-backed-live-voice-proof"),
            *proof_capture_command_section(voice),
            voice_preflight_intro,
            "",
            "```sh",
            (
                f"curl -sS -o {base}/provider-readiness.preflight.json "
                "http://127.0.0.1:8000/api/provider-readiness"
            ),
            (
                f"curl -sS -o {base}/voice-runtime-readiness.preflight.json "
                "'http://127.0.0.1:8000/api/voice-runtime-readiness?"
                "preflight_gemma=true&preflight_tts=true&preflight_livekit=true&"
                "preflight_edge=true&preflight_agent=true'"
            ),
            (
                "uv run all-about-llms-admin "
                "validate-provider-proof-preflight-artifacts --proof "
                f"provider-backed-live-voice-proof --run-id {run_id} "
                f"--preflight-dir {base} > "
                f"{base}/provider-backed-live-voice-proof.preflight-validation.json"
            ),
            "```",
            "",
            (
                "The accepted proof record must show same-run OpenRouter DeepSeek "
                "live dialogue reasoning, realtime session or LiveKit room evidence, provider "
                "smoke evidence, voice timing evidence, no failed post-capture "
                "validation checks, and a passed secret-redaction check."
            ),
            "",
            "Then create, validate, and record the proof record:",
            "",
            "```sh",
            *voice_record_commands,
            "```",
        ]

    if publication_accepted:
        publication_section = [
            "## External Publication",
            "",
            "Accepted proof status:",
            "",
            "- Accepted proof record is available.",
            "- No proof-level operator inputs remain for this proof.",
        ]
    elif publication.get("current_state") in {
        "latest_record_contains_secret_shape",
        "latest_record_has_invalid_fields",
    }:
        publication_section = audit_note_repair_section(
            "External Publication",
            publication_blocker,
        )
    elif publication.get("current_state") == "accepted_record_missing_from_some_targets":
        publication_section = audit_coverage_section(
            "External Publication",
            publication_inputs,
        )
    else:
        publication_section = [
            "## External Publication",
            "",
            "Already ready in this workspace:",
            "",
            (
                "- Approved local fixture artifact, source, claim, source ledger, "
                "and guardrail audit exist."
            ),
            "- Publication proof has a valid failed-record audit preserving the current blocker.",
            "",
            "Current blocker status:",
            "",
            f"- Current publication blocker status: `{publication_blocker_status}`",
            "",
            "Operator must still supply:",
            "",
            *[f"- {item}" for item in publication_inputs],
            "",
            *_provider_proof_operator_packet_markdown_section(
                operator_proof_packets.get("external-publication-proof")
            ),
            *proof_record_schema_section("external-publication-proof"),
            *proof_record_required_fields_section("external-publication-proof"),
            *proof_capture_command_section(publication),
            "After those inputs are available, rerun:",
            "",
            "```sh",
            (
                f"curl -sS -X POST -o {base}/publish-readiness.preflight.json "
                f"http://127.0.0.1:8000/api/runs/{run_id}/publish-readiness "
                "-H 'Content-Type: application/json' --data "
                """'{"open_feedback_gate":false,"mark_run_completed_if_ready":false,"check_publish_channel_readiness":true,"acknowledge_publish_channel_policy":true}'"""
            ),
            (
                "uv run all-about-llms-admin "
                "validate-provider-proof-preflight-artifacts --proof "
                f"external-publication-proof --run-id {run_id} "
                f"--preflight-dir {base} > "
                f"{base}/external-publication-proof.preflight-validation.json"
            ),
            "```",
            "",
            (
                "The accepted proof record must show exact destination-channel "
                "linkage, durable external destination evidence, policy "
                "acknowledgement, rollback or postcondition evidence, no failed "
                "post-capture validation checks, and a passed secret-redaction check."
            ),
            "",
            "Then create, validate, and record the proof record:",
            "",
            "```sh",
            *publication_record_commands,
            "```",
        ]

    lines = [
        "# Operator Unblocker Checklist",
        "",
        f"- checked_at: {checked_at}",
        f"- run_id: `{run_id}`",
        (
            "- generator: `uv run all-about-llms-admin "
            f"provider-proof-operator-unblocker-checklist --run-id {run_id} "
            f"--output-dir {base}`"
        ),
        (
            "- boundary: no secret values, no raw provider responses, no "
            "private audio, no blocker-state change"
        ),
        "",
        (
                "This checklist is the compact handoff for the proof records still "
                "blocking completion. The generated `README.md` remains the "
            "command source of truth; this file only narrows the next operator "
            "actions for the current UUID workspace."
            if proof_level_blockers_remain
            else (
                "This checklist is the compact handoff after accepted proof "
                "records are available. The generated `README.md` remains the "
                "command source of truth; this file only narrows the next "
                "closure actions for the current UUID workspace."
            )
        ),
        "",
        "## Current Gate",
        "",
        f"- `completion-status.json`: `{completion.get('status')}`",
        (
            "- completion evidence ref: "
            f"`{completion.get('evidence_ref', 'completion-status.json')}`"
        ),
        (
            "- `closure-review-template.json`: "
            f"`{closure.get('closure_review_template_status')}`"
        ),
        (
            "- `closure-review-status.json`: "
            f"`{closure.get('closure_review_status')}`"
        ),
        (
            "- `blocker-state-update.json`: "
            f"`{closure.get('blocker_state_update_status')}`"
        ),
        f"- state_change_allowed: `{closure.get('state_change_allowed')}`",
        f"- goal_completion_claimed: `{closure.get('goal_completion_claimed')}`",
        "- closure evidence refs:",
        *[f"  {ref}" for ref in closure_evidence_refs],
        "- completion issue codes:",
        *[f"  {code}" for code in completion_issue_codes],
        "- latest failed proofs:",
        *[f"  {proof}" for proof in latest_failed_proofs],
        "- missing accepted proofs:",
        *[f"  {proof}" for proof in missing_accepted_proofs],
        f"- completion next_action: `{completion.get('next_action', 'unknown')}`",
        "- completion next_action_commands:",
        *indented_backticked_values(
            completion.get("next_action_commands"),
            indent="  ",
        ),
        f"- Required accepted proof state: {accepted_proof_state}.",
        "",
        *operator_inputs_section,
        *credential_snapshot_section,
        *checkpoint_section,
        *voice_section,
        "",
        *publication_section,
        "",
        "## Completion Sequence",
        "",
        "Only after both accepted records validate and record successfully:",
        "",
        "```sh",
        (
            "uv run all-about-llms-admin provider-proof-completion-status "
            f"--run-id {run_id}"
        ),
        (
            "uv run all-about-llms-admin provider-proof-closure-review-template "
            f"--run-id {run_id}"
        ),
        (
            "uv run all-about-llms-admin validate-provider-proof-closure-review "
            f"--run-id {run_id} --record-path <provider-proof-closure-review.json>"
        ),
        (
            "uv run all-about-llms-admin record-provider-proof-closure-review "
            f"--run-id {run_id} --record-path <provider-proof-closure-review.json>"
        ),
        (
            "uv run all-about-llms-admin provider-proof-closure-review-status "
            f"--run-id {run_id}"
        ),
        (
            "uv run all-about-llms-admin record-provider-proof-blocker-state-update "
            f"--run-id {run_id}"
        ),
        "```",
        "",
        (
            "Do not run closure review or blocker-state update as evidence of "
            "completion while the latest proof records remain failed."
            if proof_level_blockers_remain
            else "Do not update blocker state until closure review status is approved."
        ),
    ]
    if not proof_level_blockers_remain:
        lines.insert(26, "- No proof-level operator blockers remain.")
    return "\n".join(lines) + "\n"


def _print_provider_proof_operator_unblocker_checklist(
    args: argparse.Namespace,
) -> None:
    print(_provider_proof_operator_unblocker_checklist_markdown(args), end="")


def _provider_proof_completion_proof_payload(
    proof_name: str,
    command_run_id: str,
    accepted_source_targets: list[str],
    failed_source_targets: list[str],
    secret_source_targets: list[str],
    invalid_source_targets: list[str],
    missing_source_targets: list[str],
    proof_plan: Mapping[str, object],
    status_override: str | None = None,
    output_dir: Path | None = None,
    completion_status_output_dir: Path | None = None,
) -> dict[str, object]:
    status = status_override
    if status is None:
        status = _provider_proof_completion_proof_status(
            accepted_source_targets,
            failed_source_targets,
            secret_source_targets,
            invalid_source_targets,
            missing_source_targets,
        )
    next_action = _provider_proof_completion_next_action(status)
    next_action_commands: list[str] = []
    if next_action in {
        "capture_validate_record_and_recheck",
        "replace_run_id_and_recheck",
    }:
        if status == "latest_record_failed" and output_dir is not None:
            gate_commands = _provider_proof_operator_input_gate_commands_for_proof(
                proof_name,
                command_run_id,
                output_dir,
            )
            next_action_commands = [
                *(
                    gate_commands
                    or _provider_proof_capture_commands_after_unblock(
                        proof_name,
                        command_run_id,
                        output_dir,
                    )
                ),
                *_proof_completion_status_commands(
                    command_run_id,
                    output_dir=completion_status_output_dir,
                ),
            ]
        else:
            preflight_report_files = proof_plan.get(
                "preflight_validation_report_files"
            )
            preflight_validation_path: object = "<preflight-validation.json>"
            if isinstance(preflight_report_files, list) and preflight_report_files:
                preflight_validation_path = preflight_report_files[0]
            workspace_report_files = proof_plan.get("workspace_validation_report_files")
            workspace_validation_path: object = "<workspace-validation.json>"
            if isinstance(workspace_report_files, list) and workspace_report_files:
                workspace_validation_path = workspace_report_files[0]
            next_action_commands = [
                *_proof_record_template_commands(proof_name, command_run_id),
                *_proof_record_next_commands(
                    proof_name,
                    command_run_id,
                    preflight_validation_path=preflight_validation_path,
                    workspace_validation_path=workspace_validation_path,
                ),
                *_proof_completion_status_commands(
                    command_run_id,
                    output_dir=completion_status_output_dir,
                ),
            ]
    record_proof_in = proof_plan.get("record_proof_in")
    if not isinstance(record_proof_in, list):
        record_proof_in = []
    return {
        "status": status,
        "next_action": next_action,
        "next_action_commands": next_action_commands,
        "record_proof_in": record_proof_in,
    }


def _provider_proof_completion_next_action(status: str) -> str:
    if status == "accepted_record_found":
        return "none"
    if status == "blocked_by_run_id":
        return "replace_run_id_and_recheck"
    return "capture_validate_record_and_recheck"


def _provider_proof_completion_proof_status(
    accepted_source_targets: list[str],
    failed_source_targets: list[str],
    secret_source_targets: list[str],
    invalid_source_targets: list[str],
    missing_source_targets: list[str],
) -> str:
    if failed_source_targets:
        return "latest_record_failed"
    if secret_source_targets:
        return "latest_record_contains_secret_shape"
    if invalid_source_targets:
        return "latest_record_has_invalid_fields"
    if not accepted_source_targets:
        return "missing_accepted_record"
    if missing_source_targets:
        return "accepted_record_missing_from_some_targets"
    return "accepted_record_found"


def _provider_proof_latest_audit_record_status(
    body: str,
    *,
    proof_name: str,
    run_id: str,
    expected_artifact_type: str,
    required_audit_fields: set[str],
    expected_validation_check_count: int,
) -> str | None:
    block_pattern = re.compile(
        rf"^## Provider Proof Record - {re.escape(proof_name)} - "
        rf"{re.escape(run_id)}\n(?P<body>.*?)(?=^## Provider Proof Record - |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    latest_status: str | None = None
    latest_key: tuple[bool, datetime, int] | None = None
    fallback_time = datetime.min.replace(tzinfo=timezone.utc)
    for index, match in enumerate(block_pattern.finditer(body)):
        entries = _provider_proof_audit_note_field_entries(match.group("body"))
        fields = _provider_proof_audit_note_fields_from_entries(entries)
        if fields.get("proof_artifact_type") != expected_artifact_type:
            continue
        status: str | None = None
        if (
            fields.get("proof_outcome") == "accepted"
            and fields.get("validation_status") == "valid_accepted_record"
            and fields.get("state_change_allowed") == "true"
        ):
            status = "accepted"
        elif (
            fields.get("proof_outcome") == "failed"
            and fields.get("validation_status") == "valid_failed_record"
            and fields.get("state_change_allowed") == "false"
        ):
            status = "failed"
        if status is None:
            continue
        if _provider_proof_audit_note_has_secret_shape(entries):
            status = "secret_shape_detected"
        elif (
            status == "accepted"
            and _provider_proof_audit_note_has_invalid_accepted_fields(
                fields,
                entries,
                required_audit_fields,
                expected_validation_check_count,
                proof_name=proof_name,
                expected_run_id=run_id,
            )
        ):
            status = "invalid_fields_detected"
        validation_time = _provider_proof_audit_validation_time(
            fields.get("validation_timestamp")
        )
        candidate_has_timestamp = validation_time is not None
        candidate_fallback_time = fallback_time
        if status in {"secret_shape_detected", "invalid_fields_detected"}:
            candidate_has_timestamp = True
            candidate_fallback_time = datetime.max.replace(tzinfo=timezone.utc)
        candidate_key = (
            candidate_has_timestamp,
            validation_time or candidate_fallback_time,
            index,
        )
        if latest_key is None or candidate_key > latest_key:
            latest_key = candidate_key
            latest_status = status
    return latest_status


def _provider_proof_latest_closure_review_audit_note(
    body: str,
    *,
    run_id: str,
    expected_proofs: list[str],
    expected_review_requirement_count: int,
) -> dict[str, object] | None:
    block_pattern = re.compile(
        rf"^## Provider Proof Closure Review - {re.escape(run_id)}\n"
        r"(?P<body>.*?)(?=^## Provider Proof |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    latest_note: dict[str, object] | None = None
    latest_key: tuple[bool, datetime, int] | None = None
    fallback_time = datetime.min.replace(tzinfo=timezone.utc)
    for index, match in enumerate(block_pattern.finditer(body)):
        entries = _provider_proof_audit_note_field_entries(match.group("body"))
        fields = _provider_proof_audit_note_fields_from_entries(entries)
        status: str | None = None
        if (
            fields.get("review_decision") == "approved"
            and fields.get("validation_status") == "valid_approved_closure_review"
            and fields.get("state_change_allowed") == "false"
            and fields.get("blocker_state_update_allowed_after_review") == "true"
        ):
            status = "approved"
        elif (
            fields.get("review_decision") == "rejected"
            and fields.get("validation_status") == "valid_rejected_closure_review"
            and fields.get("state_change_allowed") == "false"
            and fields.get("blocker_state_update_allowed_after_review") == "false"
        ):
            status = "rejected"
        if status is None:
            continue
        if _provider_proof_audit_note_has_secret_shape(entries):
            status = "secret_shape_detected"
        elif _provider_proof_audit_note_has_invalid_closure_review_fields(
            fields,
            entries,
            review_status=status,
            expected_proofs=expected_proofs,
            expected_review_requirement_count=expected_review_requirement_count,
        ):
            status = "invalid_fields_detected"
        review_time = _provider_proof_audit_validation_time(
            fields.get("review_timestamp")
        )
        candidate_has_timestamp = review_time is not None
        candidate_fallback_time = fallback_time
        if status in {"secret_shape_detected", "invalid_fields_detected"}:
            candidate_has_timestamp = True
            candidate_fallback_time = datetime.max.replace(tzinfo=timezone.utc)
        candidate_key = (
            candidate_has_timestamp,
            review_time or candidate_fallback_time,
            index,
        )
        if latest_key is None or candidate_key > latest_key:
            latest_key = candidate_key
            latest_note = {
                "status": status,
                "review_timestamp": fields.get("review_timestamp", ""),
                "review_time": review_time,
                "reviewer": fields.get("reviewer", ""),
                "review_decision": fields.get("review_decision", ""),
                "validation_status": fields.get("validation_status", ""),
            }
    return latest_note


def _provider_proof_audit_note_has_secret_shape(
    entries: list[tuple[str, str]],
) -> bool:
    for key, value in entries:
        if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(key):
            return True
        if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(value):
            return True
    return False


def _provider_proof_audit_note_has_invalid_closure_review_fields(
    fields: Mapping[str, str],
    entries: list[tuple[str, str]],
    *,
    review_status: str,
    expected_proofs: list[str],
    expected_review_requirement_count: int,
) -> bool:
    if _provider_proof_audit_note_has_duplicate_fields(entries):
        return True
    required_fields = {
        "checked_at",
        "review_timestamp",
        "reviewer",
        "review_decision",
        "validation_status",
        "state_change_allowed",
        "blocker_state_update_allowed_after_review",
        "validation_issues",
        "accepted_proofs",
        "review_requirements",
        "secret_redaction_check",
    }
    if _provider_proof_audit_note_missing_required_fields(fields, required_fields):
        return True
    if _provider_proof_audit_validation_time(fields.get("review_timestamp")) is None:
        return True
    if fields.get("validation_issues") != "none":
        return True
    if fields.get("secret_redaction_check") != "passed":
        return True
    if not _provider_proof_audit_note_accepted_proofs_match(
        fields.get("accepted_proofs"),
        expected_proofs,
    ):
        return True
    return not _provider_proof_audit_note_closure_review_summary_valid(
        fields.get("review_requirements"),
        review_status=review_status,
        expected_review_requirement_count=expected_review_requirement_count,
    )


def _provider_proof_audit_note_accepted_proofs_match(
    value: str | None,
    expected_proofs: list[str],
) -> bool:
    if not value:
        return False
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return False
    if not isinstance(parsed, list):
        return False
    return [str(proof) for proof in parsed] == expected_proofs


def _provider_proof_audit_note_closure_review_summary_valid(
    value: str | None,
    *,
    review_status: str,
    expected_review_requirement_count: int,
) -> bool:
    if not value:
        return False
    match = re.fullmatch(
        r"(?P<recorded>\d+) recorded / (?P<confirmed>\d+) confirmed / "
        r"(?P<rejected>\d+) rejected",
        value,
    )
    if not match:
        return False
    recorded = int(match.group("recorded"))
    confirmed = int(match.group("confirmed"))
    rejected = int(match.group("rejected"))
    if recorded <= 0 or recorded != confirmed + rejected:
        return False
    if recorded != expected_review_requirement_count:
        return False
    if review_status == "approved":
        return confirmed == recorded and rejected == 0
    return rejected > 0


def _provider_proof_audit_note_has_invalid_accepted_fields(
    fields: Mapping[str, str],
    entries: list[tuple[str, str]],
    required_audit_fields: set[str],
    expected_validation_check_count: int,
    *,
    proof_name: str,
    expected_run_id: str,
) -> bool:
    if _provider_proof_audit_note_has_duplicate_fields(entries):
        return True
    if _provider_proof_audit_note_missing_required_fields(
        fields,
        required_audit_fields,
    ):
        return True
    if _provider_proof_audit_validation_time(fields.get("validation_timestamp")) is None:
        return True
    if fields.get("secret_redaction_check") not in {"passed", "true"}:
        return True
    if fields.get("preflight_validation_report_status") != "valid_preflight_artifacts":
        return True
    if (
        fields.get("preflight_validation_report_matched_fields")
        != "all_required_fields_matched"
    ):
        return True
    if (
        fields.get("preflight_validation_report_validated_product_run_id")
        != expected_run_id
    ):
        return True
    if fields.get("workspace_validation_report_status") != "valid_workspace":
        return True
    if (
        fields.get("workspace_validation_report_matched_fields")
        != "all_required_fields_matched"
    ):
        return True
    if not _provider_proof_audit_note_validation_summary_passed(
        fields.get("post_capture_validation_results"),
        expected_validation_check_count,
    ):
        return True
    if proof_name == "provider-backed-live-voice-proof":
        validated_runtime_checks = _provider_proof_audit_note_runtime_checks(
            fields.get("preflight_validation_report_validated_runtime_checks")
        )
        if validated_runtime_checks != list(VOICE_PROOF_REQUIRED_RUNTIME_CHECKS):
            return True
        return (
            fields.get("voice_edge_benchmark_status") != "ready"
            or fields.get("execute_live_calls") != "true"
            or fields.get("realtime_provider") != "openrouter_livekit"
        )
    if proof_name == "external-publication-proof":
        destination = fields.get("durable_platform_id_or_url")
        if _provider_proof_publication_destination_is_local_substitute(destination):
            return True
        (
            validated_channels,
            publish_channel_summary_is_canonical,
        ) = _provider_proof_audit_note_publish_channels(
            fields.get("preflight_validation_report_validated_publish_channels")
        )
        if not publish_channel_summary_is_canonical:
            return True
        if not _provider_proof_external_publication_channels_are_linkedin_only(
            validated_channels
        ):
            return True
        destination_channel = fields.get("destination_channel")
        normalized_destination_channel = (
            _provider_proof_normalized_publish_channel_platform(destination_channel)
            if isinstance(destination_channel, str)
            else ""
        )
        if normalized_destination_channel != "linkedin":
            return True
        if _provider_proof_publication_destination_platform(destination) != "linkedin":
            return True
        if normalized_destination_channel not in validated_channels:
            return True
        return not _provider_proof_publication_channel_matches_destination(
            destination_channel,
            destination,
        )
    return False


def _provider_proof_audit_note_runtime_checks(value: str | None) -> list[str]:
    if not value:
        return []
    checks: list[str] = []
    for raw_check in value.split(","):
        check = raw_check.strip()
        if check:
            checks.append(check)
    return checks


def _provider_proof_audit_note_publish_channels(
    value: str | None,
) -> tuple[list[str], bool]:
    if not value:
        return [], False
    return _provider_proof_publish_channel_summary_entries(value.split(","))


def _provider_proof_required_audit_note_fields(schema: Mapping[str, object]) -> set[str]:
    raw_fields = schema.get("required_fields")
    if not isinstance(raw_fields, list):
        raise TypeError("proof_artifact_schema required_fields must be a list")
    summarized_fields = {"run_id"}
    return {str(field) for field in raw_fields if str(field) not in summarized_fields}


def _provider_proof_audit_note_missing_required_fields(
    fields: Mapping[str, str],
    required_audit_fields: set[str],
) -> bool:
    for field in required_audit_fields:
        value = fields.get(field)
        if value is None or value == "":
            return True
        if _provider_proof_record_template_placeholder(value):
            return True
    return False


def _provider_proof_audit_note_validation_summary_passed(
    value: str | None,
    expected_validation_check_count: int,
) -> bool:
    if not value:
        return False
    match = re.fullmatch(
        r"(?P<recorded>\d+) recorded / (?P<passed>\d+) passed / (?P<failed>\d+) failed",
        value,
    )
    if not match:
        return False
    return (
        int(match.group("recorded")) == expected_validation_check_count
        and int(match.group("passed")) == expected_validation_check_count
        and int(match.group("failed")) == 0
    )


def _provider_proof_audit_note_has_duplicate_fields(
    entries: list[tuple[str, str]],
) -> bool:
    seen: set[str] = set()
    for key, _value in entries:
        if key in seen:
            return True
        seen.add(key)
    return False


def _provider_proof_audit_validation_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _provider_proof_audit_note_field_entries(block: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for raw_line in block.splitlines():
        match = re.fullmatch(r"- ([A-Za-z0-9_]+): (.*)", raw_line.strip())
        if match:
            entries.append((match.group(1), match.group(2).strip()))
    return entries


def _provider_proof_audit_note_fields_from_entries(
    entries: list[tuple[str, str]],
) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key, value in entries:
        fields.setdefault(key, value)
    return fields


def _provider_proof_record_audit_targets(args: argparse.Namespace) -> list[Path]:
    raw_targets = getattr(args, "audit_target", None)
    if raw_targets:
        return [Path(target) for target in raw_targets]
    return [PROJECT_ROOT / target for target in PROVIDER_PROOF_RECORD_TARGETS]


def _provider_proof_record_audit_note(
    validation: Mapping[str, object],
    record: Mapping[str, object],
) -> str:
    schema = validation["proof_artifact_schema"]
    if not isinstance(schema, Mapping):
        raise TypeError("proof_artifact_schema must be a mapping")
    required_fields = schema["required_fields"]
    if not isinstance(required_fields, list):
        raise TypeError("proof_artifact_schema required_fields must be a list")

    proof = str(validation["proof"])
    run_id = _provider_proof_record_audit_value(record.get("run_id"))
    lines = [
        f"## Provider Proof Record - {proof} - {run_id}",
        "",
        f"- checked_at: {_provider_proof_record_audit_value(validation['checked_at'])}",
        (
            "- validation_timestamp: "
            f"{_provider_proof_record_audit_value(record.get('validation_timestamp'))}"
        ),
        f"- proof_outcome: {_provider_proof_record_audit_value(record.get('proof_outcome'))}",
        f"- validation_status: {_provider_proof_record_audit_value(validation['status'])}",
        (
            "- state_change_allowed: "
            f"{_provider_proof_record_audit_value(validation['state_change_allowed'])}"
        ),
        (
            "- proof_artifact_type: "
            f"{_provider_proof_record_audit_value(schema.get('artifact_type'))}"
        ),
        "- validation_issues: none",
    ]
    preflight_report = validation.get("preflight_validation_report")
    if isinstance(preflight_report, Mapping):
        lines.extend(
            [
                (
                    "- preflight_validation_report_status: "
                    f"{_provider_proof_record_audit_value(preflight_report.get('status'))}"
                ),
                (
                    "- preflight_validation_report_matched_fields: "
                    "all_required_fields_matched"
                ),
            ]
        )
        validated_product_run_id = preflight_report.get("validated_product_run_id")
        if isinstance(validated_product_run_id, str) and validated_product_run_id:
            lines.append(
                "- preflight_validation_report_validated_product_run_id: "
                f"{_provider_proof_record_audit_value(validated_product_run_id)}"
            )
        validated_runtime_checks = preflight_report.get("validated_runtime_checks")
        if isinstance(validated_runtime_checks, list) and validated_runtime_checks:
            runtime_text = ", ".join(str(check) for check in validated_runtime_checks)
            lines.append(
                "- preflight_validation_report_validated_runtime_checks: "
                f"{_provider_proof_record_audit_value(runtime_text)}"
            )
        validated_channels = preflight_report.get("validated_publish_channels")
        if isinstance(validated_channels, list) and validated_channels:
            channel_text = ", ".join(str(channel) for channel in validated_channels)
            lines.append(
                "- preflight_validation_report_validated_publish_channels: "
                f"{_provider_proof_record_audit_value(channel_text)}"
            )
    workspace_report = validation.get("workspace_validation_report")
    if isinstance(workspace_report, Mapping):
        lines.extend(
            [
                (
                    "- workspace_validation_report_status: "
                    f"{_provider_proof_record_audit_value(workspace_report.get('status'))}"
                ),
                (
                    "- workspace_validation_report_matched_fields: "
                    "all_required_fields_matched"
                ),
            ]
        )
    for field in required_fields:
        if field in {
            "run_id",
            "checked_at",
            "validation_timestamp",
            "proof_outcome",
            "post_capture_validation_results",
            "secret_redaction_check",
        }:
            continue
        field_text = str(field)
        lines.append(
            f"- {field_text}: {_provider_proof_record_audit_value(record.get(field_text))}"
        )

    lines.append(
        "- post_capture_validation_results: "
        f"{_provider_proof_validation_result_summary(record)}"
    )
    lines.append(
        "- secret_redaction_check: "
        f"{_provider_proof_record_audit_value(record.get('secret_redaction_check'))}"
    )
    lines.append("")
    return "\n".join(lines)


def _provider_proof_validation_result_summary(record: Mapping[str, object]) -> str:
    validation_results = record.get("post_capture_validation_results")
    if not isinstance(validation_results, Mapping):
        return "0 recorded / 0 passed / 0 failed"
    recorded = len(validation_results)
    passed = sum(1 for value in validation_results.values() if value in {True, "passed"})
    failed = recorded - passed
    return f"{recorded} recorded / {passed} passed / {failed} failed"


def _provider_proof_closure_review_audit_note(
    validation: Mapping[str, object],
    record: Mapping[str, object],
) -> str:
    lines = [
        f"## Provider Proof Closure Review - {validation['run_id']}",
        "",
        f"- checked_at: {_provider_proof_record_audit_value(validation['checked_at'])}",
        (
            "- review_timestamp: "
            f"{_provider_proof_record_audit_value(record.get('review_timestamp'))}"
        ),
        f"- reviewer: {_provider_proof_record_audit_value(record.get('reviewer'))}",
        (
            "- review_decision: "
            f"{_provider_proof_record_audit_value(record.get('review_decision'))}"
        ),
        (
            "- validation_status: "
            f"{_provider_proof_record_audit_value(validation['status'])}"
        ),
        (
            "- state_change_allowed: "
            f"{_provider_proof_record_audit_value(validation['state_change_allowed'])}"
        ),
        (
            "- blocker_state_update_allowed_after_review: "
            f"{_provider_proof_record_audit_value(validation['blocker_state_update_allowed_after_review'])}"
        ),
        "- validation_issues: none",
        (
            "- accepted_proofs: "
            f"{_provider_proof_record_audit_value(record.get('accepted_proofs'))}"
        ),
        (
            "- review_requirements: "
            f"{_provider_proof_closure_review_requirement_summary(record)}"
        ),
        (
            "- secret_redaction_check: "
            f"{_provider_proof_record_audit_value(record.get('secret_redaction_check'))}"
        ),
        "",
    ]
    return "\n".join(lines)


def _provider_proof_closure_review_requirement_summary(
    record: Mapping[str, object],
) -> str:
    review_requirements = record.get("review_requirements")
    if not isinstance(review_requirements, Mapping):
        return "0 recorded / 0 confirmed / 0 rejected"
    recorded = len(review_requirements)
    confirmed = sum(
        1 for value in review_requirements.values() if value == "confirmed"
    )
    rejected = sum(1 for value in review_requirements.values() if value == "rejected")
    return f"{recorded} recorded / {confirmed} confirmed / {rejected} rejected"


def _provider_proof_blocker_state_update_audit_note(
    status: Mapping[str, object],
) -> str:
    latest_review = status.get("latest_closure_review")
    if not isinstance(latest_review, Mapping):
        raise TypeError("latest_closure_review must be a mapping")
    candidates = status.get("state_update_candidates_after_review")
    if not isinstance(candidates, list):
        raise TypeError("state_update_candidates_after_review must be a list")
    update_pairs: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        blocker = _provider_proof_record_audit_value(candidate.get("blocker"))
        state = _provider_proof_record_audit_value(candidate.get("candidate_state"))
        update_pairs.append(f"{blocker} -> {state}")
    target_state_count = sum(
        1
        for candidate in candidates
        if isinstance(candidate, Mapping)
        and candidate.get("candidate_state") == "provider_proof_recorded_after_review"
    )
    lines = [
        f"## Provider Proof Blocker State Update - {status['run_id']}",
        "",
        f"- checked_at: {_provider_proof_record_audit_value(status['checked_at'])}",
        (
            "- idempotency_key: "
            f"{_provider_proof_blocker_state_update_idempotency_key(status)}"
        ),
        (
            "- closure_review_status: "
            f"{_provider_proof_record_audit_value(status.get('status'))}"
        ),
        (
            "- closure_review_timestamp: "
            f"{_provider_proof_record_audit_value(latest_review.get('review_timestamp'))}"
        ),
        (
            "- closure_reviewer: "
            f"{_provider_proof_record_audit_value(latest_review.get('reviewer'))}"
        ),
        "- state_change_allowed: false",
        "- blocker_state_update_allowed_by_review: true",
        "- blocker_state_update_note_recorded: true",
        "- goal_completion_claimed: false",
        (
            "- updated_blockers: "
            f"{len(update_pairs)} recorded / "
            f"{target_state_count} provider_proof_recorded_after_review"
        ),
        (
            "- updated_blocker_details: "
            f"{_provider_proof_record_audit_value('; '.join(update_pairs))}"
        ),
        "",
    ]
    return "\n".join(lines)


def _provider_proof_blocker_state_update_idempotency_key(
    status: Mapping[str, object],
) -> str:
    latest_review = status.get("latest_closure_review")
    if not isinstance(latest_review, Mapping):
        raise TypeError("latest_closure_review must be a mapping")
    candidates = status.get("state_update_candidates_after_review")
    if not isinstance(candidates, list):
        raise TypeError("state_update_candidates_after_review must be a list")
    normalized_candidates = [
        {
            "blocker": str(candidate.get("blocker")),
            "candidate_state": str(candidate.get("candidate_state")),
        }
        for candidate in candidates
        if isinstance(candidate, Mapping)
    ]
    raw_key = json.dumps(
        {
            "run_id": status.get("run_id"),
            "review_timestamp": latest_review.get("review_timestamp"),
            "reviewer": latest_review.get("reviewer"),
            "review_decision": latest_review.get("review_decision"),
            "candidates": normalized_candidates,
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


def _provider_proof_record_audit_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "n/a"
    if isinstance(value, Path):
        value = str(value)
    if not isinstance(value, str):
        value = json.dumps(value, sort_keys=True, default=str)
    for root_text in {
        str(PROJECT_ROOT),
        str(PROJECT_ROOT.resolve()),
    }:
        if root_text:
            value = value.replace(root_text, "<workspace-root>")
    if PROVIDER_PROOF_SECRET_VALUE_PATTERN.search(value):
        return "<redacted>"
    return " ".join(value.split())


def _provider_proof_audit_target_issues(
    targets: list[Path],
) -> tuple[list[dict[str, object]], list[str]]:
    issues: list[dict[str, object]] = []
    issue_codes: list[str] = []

    def add_issue(code: str, target: Path, detail: str) -> None:
        issues.append(
            {
                "code": code,
                "field": _provider_proof_output_path_text(target),
                "detail": detail,
            }
        )
        if code not in issue_codes:
            issue_codes.append(code)

    for target in targets:
        if target.exists() and not target.is_file():
            add_issue(
                "audit_target_unwritable",
                target,
                "audit target exists but is not a file",
            )
            continue
        parent = target.parent
        if parent.exists() and not parent.is_dir():
            add_issue(
                "audit_target_unwritable",
                target,
                "audit target parent exists but is not a directory",
            )
            continue
        if not parent.exists():
            for ancestor in parent.parents:
                if ancestor.exists():
                    if not ancestor.is_dir():
                        add_issue(
                            "audit_target_unwritable",
                            target,
                            "audit target ancestor exists but is not a directory",
                        )
                    break
        if target.exists():
            try:
                target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                add_issue(
                    "audit_target_unwritable",
                    target,
                    "audit target exists but is not valid UTF-8",
                )
            except OSError:
                add_issue(
                    "audit_target_unwritable",
                    target,
                    "audit target exists but is not readable",
                )
    return issues, issue_codes


def _append_provider_proof_record_audit_note(target: Path, note: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    separator = "\n\n" if existing and not existing.endswith("\n\n") else ""
    target.write_text(f"{existing}{separator}{note}", encoding="utf-8")


def _provider_proof_record_path_error_payload(
    args: argparse.Namespace,
    *,
    code: str,
    detail: str,
) -> dict[str, object]:
    proof_plan = _provider_proof_plan_payload(args)
    proof = proof_plan["proofs"].get(args.proof)
    payload: dict[str, object] = {
        "artifact": "agent-studio-provider-proof-record-validation",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": proof_plan["checked_at"],
        "proof": args.proof,
        "proof_outcome": None,
        "status": "invalid_record",
        "state_change_allowed": False,
        "issue_codes": [code],
        "issues": [
            {
                "code": code,
                "field": "record_path",
                "detail": detail,
            }
        ],
    }
    if isinstance(proof, Mapping):
        payload["command_run_id"] = proof["command_run_id"]
        payload["proof_artifact_schema"] = proof["proof_artifact_schema"]
    return payload


def _provider_proof_record_audit_path_error_payload(
    validation: Mapping[str, object],
) -> dict[str, object]:
    return {
        "artifact": "agent-studio-provider-proof-record-audit",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": validation["checked_at"],
        "proof": validation["proof"],
        "status": validation["status"],
        "validation_status": validation["status"],
        "validation_issue_codes": validation["issue_codes"],
        "audit_recorded": False,
        "state_change_allowed": False,
        "written_targets": [],
    }


def _provider_proof_closure_review_path_error_payload(
    args: argparse.Namespace,
    *,
    code: str,
    detail: str,
) -> dict[str, object]:
    proof_plan = _provider_proof_plan_payload(args)
    first_proof = next(iter(proof_plan["proofs"].values()))
    return {
        "artifact": "agent-studio-provider-proof-closure-review-validation",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": proof_plan["checked_at"],
        "run_id": str(first_proof["command_run_id"]),
        "run_id_state": first_proof["run_id_state"],
        "completion_status": "not_checked_record_path_invalid",
        "state_change_allowed": False,
        "status": "invalid_closure_review",
        "review_decision": None,
        "blocker_state_update_allowed_after_review": False,
        "issue_codes": [code],
        "issues": [
            {
                "code": code,
                "field": "record_path",
                "detail": detail,
            }
        ],
    }


def _provider_proof_closure_review_audit_path_error_payload(
    validation: Mapping[str, object],
) -> dict[str, object]:
    return {
        "artifact": "agent-studio-provider-proof-closure-review-audit",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": validation["checked_at"],
        "run_id": validation["run_id"],
        "status": validation["status"],
        "validation_status": validation["status"],
        "validation_issue_codes": validation["issue_codes"],
        "audit_recorded": False,
        "state_change_allowed": False,
        "blocker_state_update_allowed_after_review": False,
        "written_targets": [],
    }


def _load_provider_proof_record_from_path(
    args: argparse.Namespace,
) -> tuple[object | None, dict[str, object] | None]:
    try:
        record_text = args.record_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, _provider_proof_record_path_error_payload(
            args,
            code="record_path_missing",
            detail="record path is missing",
        )
    except OSError:
        return None, _provider_proof_record_path_error_payload(
            args,
            code="record_path_unreadable",
            detail="record path is unreadable",
        )
    except UnicodeDecodeError:
        return None, _provider_proof_record_path_error_payload(
            args,
            code="record_path_not_utf8",
            detail="record path is not readable as UTF-8",
        )
    try:
        return json.loads(record_text), None
    except json.JSONDecodeError:
        return None, _provider_proof_record_path_error_payload(
            args,
            code="record_path_invalid_json",
            detail="record path does not contain valid JSON",
        )


def _load_provider_proof_closure_review_from_path(
    args: argparse.Namespace,
) -> tuple[object | None, dict[str, object] | None]:
    try:
        record_text = args.record_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, _provider_proof_closure_review_path_error_payload(
            args,
            code="record_path_missing",
            detail="record path is missing",
        )
    except OSError:
        return None, _provider_proof_closure_review_path_error_payload(
            args,
            code="record_path_unreadable",
            detail="record path is unreadable",
        )
    except UnicodeDecodeError:
        return None, _provider_proof_closure_review_path_error_payload(
            args,
            code="record_path_not_utf8",
            detail="record path is not readable as UTF-8",
        )
    try:
        return json.loads(record_text), None
    except json.JSONDecodeError:
        return None, _provider_proof_closure_review_path_error_payload(
            args,
            code="record_path_invalid_json",
            detail="record path does not contain valid JSON",
        )


def _print_provider_proof_record_validation(args: argparse.Namespace) -> None:
    record, error_payload = _load_provider_proof_record_from_path(args)
    if error_payload is not None:
        print(json.dumps(error_payload, indent=2, sort_keys=True))
        return
    payload = _provider_proof_record_validation_payload(args, record)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_provider_proof_preflight_artifacts_validation(
    args: argparse.Namespace,
) -> None:
    payload = _provider_proof_preflight_artifacts_validation_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_record_provider_proof_record(args: argparse.Namespace) -> None:
    record, error_payload = _load_provider_proof_record_from_path(args)
    if error_payload is not None:
        payload = _provider_proof_record_audit_path_error_payload(error_payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    payload = _record_provider_proof_record_payload(args, record)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_record_provider_proof_closure_review(args: argparse.Namespace) -> None:
    record, error_payload = _load_provider_proof_closure_review_from_path(args)
    if error_payload is not None:
        payload = _provider_proof_closure_review_audit_path_error_payload(
            error_payload
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    payload = _record_provider_proof_closure_review_payload(args, record)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_provider_proof_completion_status(args: argparse.Namespace) -> None:
    payload = _provider_proof_completion_status_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _probability_thresholds(value: str) -> list[float]:
    thresholds = []
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            raise argparse.ArgumentTypeError(
                "threshold sweep cannot contain empty values"
            )
        try:
            threshold = float(item)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                "thresholds must be numbers between 0 and 1"
            ) from exc
        if not 0.0 <= threshold <= 1.0:
            raise argparse.ArgumentTypeError("thresholds must be between 0 and 1")
        thresholds.append(threshold)
    if not thresholds:
        raise argparse.ArgumentTypeError("at least one threshold is required")
    return thresholds


def _speech_wav_paths(args: argparse.Namespace) -> list[Path]:
    paths = []
    for raw_path in args.speech_wav or []:
        path = _project_relative_path(raw_path)
        if not path.exists():
            raise argparse.ArgumentTypeError(
                f"speech WAV fixture does not exist: {path}"
            )
        if not path.is_file():
            raise argparse.ArgumentTypeError(
                f"speech WAV fixture is not a file: {path}"
            )
        if path.suffix.lower() != ".wav":
            raise argparse.ArgumentTypeError(
                f"speech WAV fixture must end in .wav: {path}"
            )
        paths.append(path)
    for raw_dir in args.speech_wav_dir or []:
        directory = _project_relative_path(raw_dir)
        if not directory.exists():
            raise argparse.ArgumentTypeError(
                f"speech WAV directory does not exist: {directory}"
            )
        if not directory.is_dir():
            raise argparse.ArgumentTypeError(
                f"speech WAV directory is not a directory: {directory}"
            )
        fixtures = sorted(
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() == ".wav"
        )
        if not fixtures:
            raise argparse.ArgumentTypeError(
                f"speech WAV directory contains no WAV fixtures: {directory}"
            )
        paths.extend(fixtures)
    return paths


def _validate_threshold_sweep_inputs(
    args: argparse.Namespace,
    speech_paths: list[Path],
) -> None:
    if args.vad_probability_threshold_sweep and not speech_paths:
        raise argparse.ArgumentTypeError(
            "--vad-probability-threshold-sweep requires --speech-wav "
            "or --speech-wav-dir so threshold evidence uses real fixtures"
        )


async def _migrate() -> None:
    await apply_foundation_schema(get_settings())


async def _setup_checkpointer() -> None:
    await setup_postgres_checkpointer(get_settings())


async def _setup_all() -> None:
    await setup_durable_storage(get_settings())


async def _run_agent_worker(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    worker = AgentWorker(
        store,
        ContentWorkflowServices(
            gemma_provider=build_gemma_provider(settings),
            reranker_provider=build_reranker_provider(settings),
        ),
        artifacts_root=settings.artifacts_root,
        obsidian_vault_path=settings.obsidian_vault_path,
    )
    try:
        while True:
            result = await worker.run(
                args.agent_id,
                AgentWorkerRunRequest(
                    run_id=args.run_id,
                    max_tasks=args.max_tasks,
                    use_gemma=not args.disable_gemma,
                    fail_on_provider_error=args.fail_on_provider_error,
                    recover_stale_tasks=not args.disable_stale_task_recovery,
                    stale_task_after_seconds=args.stale_task_after_seconds,
                ),
            )
            print(result.model_dump_json())
            if not args.watch:
                break
            await asyncio.sleep(args.poll_interval_seconds)
    finally:
        await store.close()


async def _run_agent_cycle(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    worker = AgentWorker(
        store,
        ContentWorkflowServices(
            gemma_provider=build_gemma_provider(settings),
            reranker_provider=build_reranker_provider(settings),
        ),
        artifacts_root=settings.artifacts_root,
        obsidian_vault_path=settings.obsidian_vault_path,
    )
    agent_ids = args.agent_id or []
    try:
        while True:
            result = await worker.run_cycle(
                AgentWorkerCycleRequest(
                    run_id=UUID(args.run_id),
                    agent_ids=agent_ids,
                    max_tasks_per_agent=args.max_tasks_per_agent,
                    max_rounds=args.max_rounds,
                    use_gemma=not args.disable_gemma,
                    fail_on_provider_error=args.fail_on_provider_error,
                    recover_stale_tasks=not args.disable_stale_task_recovery,
                    stale_task_after_seconds=args.stale_task_after_seconds,
                ),
            )
            print(result.model_dump_json())
            if not args.watch:
                break
            await asyncio.sleep(args.poll_interval_seconds)
    finally:
        await store.close()


async def _run_worker_profile(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    worker = AgentWorker(
        store,
        ContentWorkflowServices(
            gemma_provider=build_gemma_provider(settings),
            reranker_provider=build_reranker_provider(settings),
        ),
        artifacts_root=settings.artifacts_root,
        obsidian_vault_path=settings.obsidian_vault_path,
    )
    try:
        while True:
            result = await worker.run_profile_heartbeat(UUID(args.profile_id))
            print(result.model_dump_json())
            if not args.watch:
                break
            await asyncio.sleep(result.profile.poll_interval_seconds)
    finally:
        await store.close()


async def _run_worker_scheduler(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    worker = AgentWorker(
        store,
        ContentWorkflowServices(
            gemma_provider=build_gemma_provider(settings),
            reranker_provider=build_reranker_provider(settings),
        ),
        artifacts_root=settings.artifacts_root,
        obsidian_vault_path=settings.obsidian_vault_path,
    )
    request = _worker_scheduler_request_from_args(args)
    iterations = 0
    try:
        while True:
            iterations += 1
            result = await worker.run_due_profile_scheduler(request)
            print(result.model_dump_json())
            if not args.watch:
                break
            if args.max_iterations is not None and iterations >= args.max_iterations:
                break
            await asyncio.sleep(args.poll_interval_seconds)
    finally:
        await store.close()


def _worker_scheduler_request_from_args(
    args: argparse.Namespace,
) -> WorkerSchedulerRunRequest:
    return WorkerSchedulerRunRequest(
        max_profiles=args.max_profiles,
        run_id=UUID(args.run_id) if args.run_id else None,
        execution_mode=args.execution_mode,
    )


def _livekit_voice_timing_capture_request_from_args(
    args: argparse.Namespace,
) -> LiveKitVoiceTimingCaptureRequest:
    transcript = args.transcript.strip() if args.transcript else None
    voice = args.voice.strip() if args.voice else None
    return LiveKitVoiceTimingCaptureRequest(
        realtime_session_id=(
            UUID(args.realtime_session_id) if args.realtime_session_id else None
        ),
        timeout_seconds=args.timeout_seconds,
        audio_probe_duration_ms=args.audio_probe_duration_ms,
        post_speech_silence_ms=args.post_speech_silence_ms,
        interrupt_on_first_output=not args.no_interrupt,
        transcript=transcript or None,
        voice=voice or None,
    )


async def _run_autonomous_pass(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    services = ContentWorkflowServices(
        search_provider=build_search_provider(settings),
        gemma_provider=build_gemma_provider(settings),
        reranker_provider=build_reranker_provider(settings),
    )
    try:
        result = await AutonomousStudioPassWorkflow(
            store,
            settings.artifacts_root,
            services,
            obsidian_vault_path=settings.obsidian_vault_path,
            settings=settings,
            realtime_provider_factory=(
                lambda provider=None: build_realtime_provider(settings, provider)
            ),
        ).run(
            UUID(args.run_id),
            AutonomousStudioPassRequest(
                agent_ids=args.agent_id or [],
                max_tasks_per_agent=args.max_tasks_per_agent,
                max_worker_rounds=args.max_worker_rounds,
                run_runtime_health_check=not args.skip_runtime_health,
                block_on_runtime_health_blocked=not args.ignore_runtime_health_block,
                build_research_freshness_ledger=not args.skip_research_freshness,
                auto_refresh_research_sources=not args.skip_research_source_refresh,
                block_on_research_freshness_blocked=not args.ignore_research_freshness_block,
                build_retrieval_quality_ledger=not args.skip_retrieval_quality,
                block_on_retrieval_quality_blocked=not args.ignore_retrieval_quality_block,
                retrieval_quality_candidate_window=args.retrieval_quality_candidate_window,
                retrieval_quality_min_accepted_sources=args.retrieval_quality_min_accepted_sources,
                build_a2a_collaboration_graph=not args.skip_a2a_graph,
                block_on_a2a_graph_blocked=not args.ignore_a2a_graph_block,
                block_on_open_feedback=not args.ignore_open_feedback_block,
                continue_multimodal_followups=not args.skip_multimodal_followups,
                multimodal_followup_rounds=args.multimodal_followup_rounds,
                run_worker_cycle=not args.skip_worker_cycle,
                build_missing_media_plans=not args.skip_media,
                build_distribution_package=not args.skip_distribution,
                refresh_source_ledger=not args.skip_source_ledger,
                run_guardrail_audit=not args.skip_guardrails,
                check_publish_readiness=not args.skip_readiness,
                build_artifact_index=not args.skip_artifact_index,
                build_work_plan=not args.skip_work_plan,
                record_sync_pulse=not args.skip_sync_pulse,
                build_context_packet=not args.skip_context_packet,
                context_packet_agent_id=args.context_packet_agent_id,
                export_memory_summary_to_obsidian=args.export_memory_summary_to_obsidian,
                memory_summary_agent_id=args.memory_summary_agent_id,
                memory_summary_limit=args.memory_summary_limit,
                build_skill_usage_ledger=not args.skip_skill_usage_ledger,
                build_model_routing_ledger=not args.skip_model_routing_ledger,
                build_provider_smoke_ledger=not args.skip_provider_smoke_ledger,
                provider_smoke_execute_live_calls=args.provider_smoke_live,
                provider_smoke_realtime_provider=args.provider_smoke_realtime_provider,
                provider_smoke_voice=args.provider_smoke_voice,
                provider_smoke_search_query=args.provider_smoke_search_query,
                build_provider_ops_ledger=not args.skip_provider_ops_ledger,
                build_realtime_dialogue_ledger=not args.skip_realtime_dialogue_ledger,
                build_feedback_resolution_ledger=not args.skip_feedback_resolution_ledger,
                build_foundation_audit=not args.skip_foundation_audit,
                build_run_replay_ledger=not args.skip_run_replay_ledger,
                generate_interactive_note=args.generate_note,
                open_feedback_gate=not args.disable_feedback_gate,
                use_gemma=not args.disable_gemma,
                fail_on_provider_error=args.fail_on_provider_error,
                include_replay_event_payloads=args.include_replay_event_payloads,
                notes=args.notes,
            ),
        )
        print(result.model_dump_json())
    finally:
        await store.close()


async def _build_distribution_package(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    try:
        result = await DistributionPackageWorkflow(store).run(
            UUID(args.run_id),
            DistributionPackageRequest(
                platforms=args.platform or [],
                audience=args.audience,
                campaign_goal=args.campaign_goal,
                include_outreach=not args.skip_outreach,
                created_by_agent_id=args.agent_id,
            ),
        )
        print(result.model_dump_json())
    finally:
        await store.close()


async def _build_provider_smoke_ledger(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    services = ContentWorkflowServices(
        search_provider=build_search_provider(settings),
        gemma_provider=build_gemma_provider(settings),
        reranker_provider=build_reranker_provider(settings),
    )
    try:
        result = await ProviderSmokeWorkflow(
            store,
            settings,
            services,
            realtime_provider_factory=(
                lambda provider=None: build_realtime_provider(settings, provider)
            ),
        ).build(
            UUID(args.run_id),
            ProviderSmokeRunRequest(
                record_artifact=not args.no_artifact,
                execute_live_calls=args.live,
                topic=args.topic,
                realtime_provider=args.realtime_provider,
                voice=args.voice,
                search_query=args.search_query,
                event_limit=args.event_limit,
                include_gemma=not args.skip_gemma,
                include_realtime=not args.skip_realtime,
                include_web_search=not args.skip_web_search,
                include_reranker=not args.skip_reranker,
                include_imagegen_boundary=not args.skip_imagegen_boundary,
            ),
        )
        print(result.model_dump_json())
    finally:
        await store.close()


async def _resume_run(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    services = ContentWorkflowServices(
        gemma_provider=build_gemma_provider(settings),
        reranker_provider=build_reranker_provider(settings),
    )
    try:
        result = await RunResumeWorkflow(store).resume_run(
            UUID(args.run_id),
            RunResumeRequest(
                agent_id=args.agent_id,
                agent_ids=args.worker_agent_id or [],
                create_checkpoint=not args.skip_checkpoint,
                build_work_plan=not args.skip_work_plan,
                create_followup_tasks=not args.skip_followup_tasks,
                heartbeat_active_profiles=not args.skip_active_profiles,
                run_worker_cycle=not args.skip_worker_cycle,
                max_tasks_per_agent=args.max_tasks_per_agent,
                max_worker_rounds=args.max_worker_rounds,
                use_gemma=not args.disable_gemma,
                fail_on_provider_error=args.fail_on_provider_error,
                notes=args.notes,
            ),
            services,
        )
        print(result.model_dump_json())
    finally:
        await store.close()


async def _run_sync_pulse(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    try:
        result = await RunSyncPulseWorkflow(store).build(
            UUID(args.run_id),
            RunSyncPulseRequest(
                record_artifact=not args.no_artifact,
                build_work_plan=not args.skip_work_plan,
                create_followup_tasks=args.create_followup_tasks,
                include_completed_tasks=args.include_completed_tasks,
                max_work_items=args.max_work_items,
                notes=args.notes,
            ),
        )
        print(result.model_dump_json())
    finally:
        await store.close()


async def _build_runtime_health_ledger(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    try:
        result = await RuntimeHealthLedgerWorkflow(store, settings=settings).build(
            UUID(args.run_id),
            RuntimeHealthLedgerRequest(
                record_artifact=not args.no_artifact,
                event_limit=args.event_limit,
                include_static_checks=not args.skip_static_checks,
                include_run_evidence=not args.skip_run_evidence,
                record_live_store_evidence=not args.skip_live_store_evidence,
                include_voice_edge_benchmark=not args.skip_voice_edge_benchmark,
            ),
        )
        print(result.model_dump_json())
    finally:
        await store.close()


async def _build_cockpit_walkthrough_ledger(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    try:
        result = await CockpitWalkthroughLedgerWorkflow(store).build(
            UUID(args.run_id),
            CockpitWalkthroughLedgerRequest(
                record_artifact=not args.no_artifact,
                event_limit=args.event_limit,
                include_runtime_health=not args.skip_runtime_health,
                include_static_runtime_checks=not args.skip_static_runtime_checks,
                record_live_store_evidence=not args.skip_live_store_evidence,
            ),
            provider_readiness=build_provider_readiness(settings),
        )
        print(result.model_dump_json())
    finally:
        await store.close()


async def _build_realtime_voice_timing_ledger(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    try:
        result = await RealtimeVoiceTimingLedgerWorkflow(store).build(
            UUID(args.run_id),
            RealtimeVoiceTimingLedgerRequest(
                record_artifact=not args.no_artifact,
                event_limit=args.event_limit,
            ),
        )
        print(result.model_dump_json())
    finally:
        await store.close()


async def _capture_livekit_voice_timing_proof(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = await PostgresStore.from_settings(settings)
    try:
        result = await LiveKitVoiceTimingCaptureWorkflow(
            store,
            settings=settings,
        ).capture(
            UUID(args.run_id),
            _livekit_voice_timing_capture_request_from_args(args),
        )
        print(result.model_dump_json())
    finally:
        await store.close()


async def _run_voice_agent(args: argparse.Namespace) -> None:
    await run_livekit_voice_agent_server(
        devmode=args.dev,
        unregistered=args.unregistered,
        settings=get_settings(),
    )


async def _benchmark_voice_edge(args: argparse.Namespace) -> None:
    settings = get_settings()
    client_kwargs = {
        "timeout_seconds": (
            args.timeout_seconds or settings.rust_voice_edge_timeout_seconds
        ),
        "sample_rate": settings.gemma4_realtime_sample_rate,
        "frame_ms": settings.rust_voice_edge_frame_ms,
        "vad_backend": args.vad_backend or settings.rust_voice_edge_vad_backend,
        "target_vad_model": settings.gemma4_realtime_rust_vad_model,
        "vad_model_path": args.vad_model_path or settings.rust_voice_edge_vad_model_path,
        "allow_vad_fallback": (
            settings.rust_voice_edge_allow_vad_fallback and not args.no_vad_fallback
        ),
        "vad_threshold": (
            args.vad_threshold
            if args.vad_threshold is not None
            else settings.rust_voice_edge_vad_threshold
        ),
        "vad_probability_threshold": (
            args.vad_probability_threshold
            if args.vad_probability_threshold is not None
            else settings.rust_voice_edge_vad_probability_threshold
        ),
        "vad_session_pool_size": (
            args.vad_session_pool_size
            if args.vad_session_pool_size is not None
            else settings.rust_voice_edge_vad_session_pool_size
        ),
        "vad_stream_state_cache_size": (
            args.vad_stream_state_cache_size
            if args.vad_stream_state_cache_size is not None
            else settings.rust_voice_edge_vad_stream_state_cache_size
        ),
        "min_speech_frames": (
            args.min_speech_frames
            if args.min_speech_frames is not None
            else settings.rust_voice_edge_min_speech_frames
        ),
        "max_inbound_buffer_bytes": settings.rust_voice_edge_max_inbound_buffer_bytes,
        "max_outbound_buffer_bytes": settings.rust_voice_edge_max_outbound_buffer_bytes,
    }
    if args.http_url:
        client = RustVoiceEdgeHttpClient(base_url=args.http_url, **client_kwargs)
    else:
        client = PersistentRustVoiceEdgeClient(
            binary_path=args.binary_path or settings.rust_voice_edge_binary_path,
            **client_kwargs,
        )
    try:
        speech_paths = _speech_wav_paths(args)
        _validate_threshold_sweep_inputs(args, speech_paths)
        speech_fixtures = []
        for path in speech_paths:
            try:
                speech_fixtures.append(
                    load_wav_speech_fixture(
                        path,
                        expected_sample_rate=client.sample_rate,
                    )
                )
            except (OSError, ValueError, EOFError) as exc:
                raise argparse.ArgumentTypeError(
                    f"failed to load speech WAV fixture {path}: {exc}"
                ) from exc
        config = VoiceEdgeBenchmarkConfig(
            runs_per_scenario=args.runs_per_scenario,
            samples_per_frame=args.samples_per_frame,
            speech_amplitude=args.speech_amplitude,
            concurrent_streams=args.concurrent_streams,
            concurrent_iterations=args.concurrent_iterations,
            max_speech_frames=args.max_speech_frames,
            frame_ms=client.frame_ms,
        )
        if args.vad_probability_threshold_sweep:
            result = await run_voice_edge_threshold_sweep(
                client,
                thresholds=args.vad_probability_threshold_sweep,
                fixtures=speech_fixtures,
                config=config,
            )
        elif speech_fixtures:
            result = await run_voice_edge_benchmark_corpus(
                client,
                fixtures=speech_fixtures,
                config=config,
            )
        else:
            result = await run_voice_edge_benchmark(client, config=config)
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="all-about-llms-admin")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate", help="Apply Postgres + pgvector app schema.")
    subparsers.add_parser(
        "setup-checkpointer",
        help="Create or upgrade LangGraph Postgres checkpoint tables.",
    )
    subparsers.add_parser(
        "setup-durable-storage",
        help="Apply app schema and LangGraph checkpoint tables.",
    )
    blocker_snapshot_parser = subparsers.add_parser(
        "blocker-credential-snapshot",
        help=(
            "Print no-secret credential snapshots for the remaining live voice "
            "and publication blockers."
        ),
    )
    blocker_snapshot_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    blocker_snapshot_parser.add_argument(
        "--operator-input-path",
        type=_project_relative_path,
        help=(
            "Optional filled no-secret operator input file to merge into the "
            "credential classifier without printing values."
        ),
    )
    blocker_snapshot_parser.add_argument("--checked-at")
    proof_plan_parser = subparsers.add_parser(
        "provider-proof-plan",
        help=(
            "Print the next provider-backed proof actions without calling "
            "external providers or printing secret values."
        ),
    )
    proof_plan_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    proof_plan_parser.add_argument(
        "--operator-input-path",
        type=_project_relative_path,
        help=(
            "Optional filled no-secret operator input file to merge into the "
            "credential classifier without printing values."
        ),
    )
    proof_plan_parser.add_argument("--checked-at")
    proof_plan_parser.add_argument("--run-id", default="<run-id>")
    proof_bootstrap_validation_parser = subparsers.add_parser(
        "validate-provider-proof-product-run-bootstrap",
        help=(
            "Validate a captured POST /api/runs response before initializing "
            "a provider proof workspace."
        ),
    )
    proof_bootstrap_validation_parser.add_argument("--checked-at")
    proof_bootstrap_validation_parser.add_argument(
        "--create-response-path",
        type=_project_relative_path,
        required=True,
    )
    proof_bootstrap_workspace_parser = subparsers.add_parser(
        "init-provider-proof-workspace-from-bootstrap",
        help=(
            "Validate a captured POST /api/runs response and initialize the "
            "UUID-named provider proof workspace."
        ),
    )
    proof_bootstrap_workspace_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    proof_bootstrap_workspace_parser.add_argument("--checked-at")
    proof_bootstrap_workspace_parser.add_argument(
        "--create-response-path",
        type=_project_relative_path,
        required=True,
    )
    proof_bootstrap_workspace_parser.add_argument(
        "--output-root",
        type=_project_relative_path,
        default=PROJECT_ROOT / "social_media_optimiser/output/provider-proof",
    )
    proof_template_parser = subparsers.add_parser(
        "provider-proof-record-template",
        help=(
            "Print a no-secret draft proof-record JSON template for live voice "
            "or publication proof capture."
        ),
    )
    proof_template_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    proof_template_parser.add_argument("--checked-at")
    proof_template_parser.add_argument("--run-id", default="<run-id>")
    proof_template_parser.add_argument(
        "--proof",
        choices=[
            "provider-backed-live-voice-proof",
            "external-publication-proof",
        ],
        required=True,
    )
    proof_workspace_parser = subparsers.add_parser(
        "init-provider-proof-workspace",
        help=(
            "Create a no-secret run-specific workspace with draft proof-record "
            "templates and capture instructions."
        ),
    )
    proof_workspace_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    proof_workspace_parser.add_argument("--checked-at")
    proof_workspace_parser.add_argument("--run-id", required=True)
    proof_workspace_parser.add_argument(
        "--output-dir",
        type=_project_relative_path,
        required=True,
    )
    proof_workspace_validation_parser = subparsers.add_parser(
        "validate-provider-proof-workspace",
        help=(
            "Validate a no-secret provider proof workspace still matches the "
            "current proof plan before live proof capture."
        ),
    )
    proof_workspace_validation_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    proof_workspace_validation_parser.add_argument("--checked-at")
    proof_workspace_validation_parser.add_argument("--run-id", required=True)
    proof_workspace_validation_parser.add_argument(
        "--output-dir",
        type=_project_relative_path,
        required=True,
    )
    operator_input_readiness_parser = subparsers.add_parser(
        "provider-proof-operator-input-readiness",
        help=(
            "Validate a filled no-secret operator input file before refreshing "
            "credential snapshots or proof preflights."
        ),
    )
    operator_input_readiness_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    operator_input_readiness_parser.add_argument("--checked-at")
    operator_input_readiness_parser.add_argument("--run-id", required=True)
    operator_input_readiness_parser.add_argument(
        "--input-path",
        type=_project_relative_path,
        required=True,
    )
    operator_input_readiness_parser.add_argument(
        "--fail-on-blocked",
        action="store_true",
        help=(
            "Exit nonzero after printing the JSON payload unless all required "
            "operator inputs are ready for credential snapshot refresh."
        ),
    )
    proof_record_parser = subparsers.add_parser(
        "validate-provider-proof-record",
        help=(
            "Validate a captured provider proof record against the no-secret "
            "provider proof-plan schema without changing blocker state."
        ),
    )
    proof_record_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    proof_record_parser.add_argument("--checked-at")
    proof_record_parser.add_argument("--run-id", default="<run-id>")
    proof_record_parser.add_argument(
        "--proof",
        choices=[
            "provider-backed-live-voice-proof",
            "external-publication-proof",
        ],
        required=True,
    )
    proof_record_parser.add_argument(
        "--record-path",
        type=_project_relative_path,
        required=True,
    )
    proof_record_parser.add_argument(
        "--preflight-validation-path",
        type=_project_relative_path,
        help=(
            "Optional no-secret preflight validation report to cross-check "
            "required preflight artifact IDs."
        ),
    )
    proof_record_parser.add_argument(
        "--workspace-validation-path",
        type=_project_relative_path,
        help=(
            "Optional no-secret workspace validation report to cross-check "
            "proof templates and README before accepting a proof record."
        ),
    )
    preflight_artifacts_parser = subparsers.add_parser(
        "validate-provider-proof-preflight-artifacts",
        help=(
            "Validate captured preflight JSON files for a provider proof "
            "without printing secret values or changing blocker state."
        ),
    )
    preflight_artifacts_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    preflight_artifacts_parser.add_argument("--checked-at")
    preflight_artifacts_parser.add_argument("--run-id", required=True)
    preflight_artifacts_parser.add_argument(
        "--proof",
        choices=[
            "provider-backed-live-voice-proof",
            "external-publication-proof",
        ],
        required=True,
    )
    preflight_artifacts_parser.add_argument(
        "--preflight-dir",
        type=_project_relative_path,
        required=True,
    )
    record_proof_parser = subparsers.add_parser(
        "record-provider-proof-record",
        help=(
            "Validate a captured provider proof record and append a redacted "
            "audit note to the configured vault proof targets."
        ),
    )
    record_proof_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    record_proof_parser.add_argument("--checked-at")
    record_proof_parser.add_argument("--run-id", default="<run-id>")
    record_proof_parser.add_argument(
        "--proof",
        choices=[
            "provider-backed-live-voice-proof",
            "external-publication-proof",
        ],
        required=True,
    )
    record_proof_parser.add_argument(
        "--record-path",
        type=_project_relative_path,
        required=True,
    )
    record_proof_parser.add_argument(
        "--preflight-validation-path",
        type=_project_relative_path,
        help=(
            "Optional no-secret preflight validation report to cross-check "
            "required preflight artifact IDs before audit recording."
        ),
    )
    record_proof_parser.add_argument(
        "--workspace-validation-path",
        type=_project_relative_path,
        help=(
            "Optional no-secret workspace validation report to cross-check "
            "proof templates and README before audit recording."
        ),
    )
    record_proof_parser.add_argument(
        "--audit-target",
        action="append",
        type=_project_relative_path,
        help=(
            "Override a default vault audit target; repeat for multiple targets."
        ),
    )
    proof_completion_parser = subparsers.add_parser(
        "provider-proof-completion-status",
        help=(
            "Check configured vault audit targets for accepted provider proof "
            "records without changing blocker state."
        ),
    )
    proof_completion_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    proof_completion_parser.add_argument("--checked-at")
    proof_completion_parser.add_argument("--run-id", required=True)
    proof_completion_parser.add_argument(
        "--output-dir",
        type=_project_relative_path,
        help=(
            "Provider proof workspace directory used to read current "
            "operator-input readiness and emit recovery commands."
        ),
    )
    proof_completion_parser.add_argument(
        "--audit-target",
        action="append",
        type=_project_relative_path,
        help=(
            "Override a default vault audit target; repeat for multiple targets."
        ),
    )
    proof_closure_template_parser = subparsers.add_parser(
        "provider-proof-closure-review-template",
        help=(
            "Print a no-secret closure-review template after provider proof "
            "completion status accepts all required records."
        ),
    )
    proof_closure_template_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    proof_closure_template_parser.add_argument("--checked-at")
    proof_closure_template_parser.add_argument("--run-id", required=True)
    proof_closure_template_parser.add_argument(
        "--audit-target",
        action="append",
        type=_project_relative_path,
        help=(
            "Override a default vault audit target; repeat for multiple targets."
        ),
    )
    proof_closure_validation_parser = subparsers.add_parser(
        "validate-provider-proof-closure-review",
        help=(
            "Validate a filled provider proof closure-review record without "
            "changing blocker state."
        ),
    )
    proof_closure_validation_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    proof_closure_validation_parser.add_argument("--checked-at")
    proof_closure_validation_parser.add_argument("--run-id", required=True)
    proof_closure_validation_parser.add_argument(
        "--record-path",
        type=_project_relative_path,
        required=True,
    )
    proof_closure_validation_parser.add_argument(
        "--audit-target",
        action="append",
        type=_project_relative_path,
        help=(
            "Override a default vault audit target; repeat for multiple targets."
        ),
    )
    record_closure_review_parser = subparsers.add_parser(
        "record-provider-proof-closure-review",
        help=(
            "Validate a filled closure-review record and append a redacted "
            "audit note without changing blocker state."
        ),
    )
    record_closure_review_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    record_closure_review_parser.add_argument("--checked-at")
    record_closure_review_parser.add_argument("--run-id", required=True)
    record_closure_review_parser.add_argument(
        "--record-path",
        type=_project_relative_path,
        required=True,
    )
    record_closure_review_parser.add_argument(
        "--proof-audit-target",
        action="append",
        type=_project_relative_path,
        help=(
            "Override the proof-record audit target used for completion-status "
            "validation; repeat for multiple targets."
        ),
    )
    record_closure_review_parser.add_argument(
        "--audit-target",
        action="append",
        type=_project_relative_path,
        help=(
            "Override the closure-review audit target; repeat for multiple targets."
        ),
    )
    closure_review_status_parser = subparsers.add_parser(
        "provider-proof-closure-review-status",
        help=(
            "Read recorded closure-review audit notes without changing blocker "
            "state."
        ),
    )
    closure_review_status_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    closure_review_status_parser.add_argument("--checked-at")
    closure_review_status_parser.add_argument("--run-id", required=True)
    closure_review_status_parser.add_argument(
        "--proof-audit-target",
        action="append",
        type=_project_relative_path,
        help=(
            "Override the proof-record audit target used for completion-status "
            "validation; repeat for multiple targets."
        ),
    )
    closure_review_status_parser.add_argument(
        "--audit-target",
        action="append",
        type=_project_relative_path,
        help=(
            "Override the closure-review audit target; repeat for multiple targets."
        ),
    )
    closure_review_status_parser.add_argument(
        "--blocker-update-audit-target",
        action="append",
        type=_project_relative_path,
        help=(
            "Include a blocker-state update write target in approved next-action "
            "commands; repeat for multiple targets."
        ),
    )
    blocker_state_update_parser = subparsers.add_parser(
        "record-provider-proof-blocker-state-update",
        help=(
            "Append a no-secret blocker-state update audit note after approved "
            "provider proof closure review."
        ),
    )
    blocker_state_update_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    blocker_state_update_parser.add_argument("--checked-at")
    blocker_state_update_parser.add_argument("--run-id", required=True)
    blocker_state_update_parser.add_argument(
        "--proof-audit-target",
        action="append",
        type=_project_relative_path,
        help=(
            "Override the proof-record audit target used for completion-status "
            "validation; repeat for multiple targets."
        ),
    )
    blocker_state_update_parser.add_argument(
        "--closure-review-audit-target",
        action="append",
        type=_project_relative_path,
        help=(
            "Override the closure-review audit target used for approved-review "
            "status; repeat for multiple targets."
        ),
    )
    blocker_state_update_parser.add_argument(
        "--audit-target",
        action="append",
        type=_project_relative_path,
        help=(
            "Override the blocker-state update audit target; repeat for "
            "multiple targets."
        ),
    )
    blocker_matrix_parser = subparsers.add_parser(
        "provider-proof-current-blocker-matrix",
        help=(
            "Read current provider proof artifacts and print a no-secret "
            "matrix of already-evidenced readiness versus remaining blockers."
        ),
    )
    blocker_matrix_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    blocker_matrix_parser.add_argument("--checked-at")
    blocker_matrix_parser.add_argument("--run-id", required=True)
    blocker_matrix_parser.add_argument(
        "--output-dir",
        type=_project_relative_path,
        help=(
            "Provider proof workspace directory; defaults to "
            "social_media_optimiser/output/provider-proof/<run-id>."
        ),
    )
    current_status_parser = subparsers.add_parser(
        "provider-proof-current-status",
        help=(
            "Read current provider proof artifacts and print a no-secret "
            "Markdown status packet for the proof workspace."
        ),
    )
    current_status_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    current_status_parser.add_argument("--checked-at")
    current_status_parser.add_argument("--run-id", required=True)
    current_status_parser.add_argument(
        "--output-dir",
        type=_project_relative_path,
        help=(
            "Provider proof workspace directory; defaults to "
            "social_media_optimiser/output/provider-proof/<run-id>."
        ),
    )
    unblocker_checklist_parser = subparsers.add_parser(
        "provider-proof-operator-unblocker-checklist",
        help=(
            "Read current provider proof artifacts and print the compact "
            "operator checklist for the remaining proof blockers."
        ),
    )
    unblocker_checklist_parser.add_argument(
        "--env-example-path",
        type=_project_relative_path,
        default=PROJECT_ROOT / ".env.example",
    )
    unblocker_checklist_parser.add_argument("--checked-at")
    unblocker_checklist_parser.add_argument("--run-id", required=True)
    unblocker_checklist_parser.add_argument(
        "--output-dir",
        type=_project_relative_path,
        help=(
            "Provider proof workspace directory; defaults to "
            "social_media_optimiser/output/provider-proof/<run-id>."
        ),
    )
    worker_parser = subparsers.add_parser(
        "run-agent-worker",
        help="Run one durable A2A worker pass, or watch for accepted tasks.",
    )
    worker_parser.add_argument("--run-id", required=True)
    worker_parser.add_argument("--agent-id", required=True)
    worker_parser.add_argument("--max-tasks", type=int, default=1)
    worker_parser.add_argument("--watch", action="store_true")
    worker_parser.add_argument("--poll-interval-seconds", type=float, default=5.0)
    worker_parser.add_argument("--disable-gemma", action="store_true")
    worker_parser.add_argument("--fail-on-provider-error", action="store_true")
    worker_parser.add_argument("--disable-stale-task-recovery", action="store_true")
    worker_parser.add_argument("--stale-task-after-seconds", type=float, default=3600.0)
    cycle_parser = subparsers.add_parser(
        "run-agent-cycle",
        help="Run multiple durable A2A workers in sequence, or watch continuously.",
    )
    cycle_parser.add_argument("--run-id", required=True)
    cycle_parser.add_argument("--agent-id", action="append")
    cycle_parser.add_argument("--max-tasks-per-agent", type=int, default=1)
    cycle_parser.add_argument("--max-rounds", type=int, default=1)
    cycle_parser.add_argument("--watch", action="store_true")
    cycle_parser.add_argument("--poll-interval-seconds", type=float, default=5.0)
    cycle_parser.add_argument("--disable-gemma", action="store_true")
    cycle_parser.add_argument("--fail-on-provider-error", action="store_true")
    cycle_parser.add_argument("--disable-stale-task-recovery", action="store_true")
    cycle_parser.add_argument("--stale-task-after-seconds", type=float, default=3600.0)
    profile_parser = subparsers.add_parser(
        "run-worker-profile",
        help="Run heartbeat cycles for a saved durable worker profile.",
    )
    profile_parser.add_argument("--profile-id", required=True)
    profile_parser.add_argument("--watch", action="store_true")
    scheduler_parser = subparsers.add_parser(
        "run-worker-scheduler",
        help="Discover active due worker profiles and heartbeat them.",
    )
    scheduler_parser.add_argument("--max-profiles", type=int, default=25)
    scheduler_parser.add_argument("--run-id")
    scheduler_parser.add_argument(
        "--execution-mode",
        choices=["worker_cycle", "autonomous_pass"],
    )
    scheduler_parser.add_argument("--watch", action="store_true")
    scheduler_parser.add_argument("--poll-interval-seconds", type=float, default=5.0)
    scheduler_parser.add_argument("--max-iterations", type=_positive_int)
    pass_parser = subparsers.add_parser(
        "run-autonomous-pass",
        help="Run one bounded autonomous studio pass for a durable run.",
    )
    pass_parser.add_argument("--run-id", required=True)
    pass_parser.add_argument("--agent-id", action="append")
    pass_parser.add_argument("--max-tasks-per-agent", type=int, default=1)
    pass_parser.add_argument("--max-worker-rounds", type=int, default=1)
    pass_parser.add_argument("--skip-runtime-health", action="store_true")
    pass_parser.add_argument("--ignore-runtime-health-block", action="store_true")
    pass_parser.add_argument("--skip-research-freshness", action="store_true")
    pass_parser.add_argument("--skip-research-source-refresh", action="store_true")
    pass_parser.add_argument("--ignore-research-freshness-block", action="store_true")
    pass_parser.add_argument("--skip-retrieval-quality", action="store_true")
    pass_parser.add_argument("--ignore-retrieval-quality-block", action="store_true")
    pass_parser.add_argument("--retrieval-quality-candidate-window", type=int, default=30)
    pass_parser.add_argument("--retrieval-quality-min-accepted-sources", type=int, default=2)
    pass_parser.add_argument("--skip-a2a-graph", action="store_true")
    pass_parser.add_argument("--ignore-a2a-graph-block", action="store_true")
    pass_parser.add_argument("--ignore-open-feedback-block", action="store_true")
    pass_parser.add_argument("--skip-multimodal-followups", action="store_true")
    pass_parser.add_argument("--multimodal-followup-rounds", type=int, default=1)
    pass_parser.add_argument("--skip-worker-cycle", action="store_true")
    pass_parser.add_argument("--skip-media", action="store_true")
    pass_parser.add_argument("--skip-distribution", action="store_true")
    pass_parser.add_argument("--skip-source-ledger", action="store_true")
    pass_parser.add_argument("--skip-guardrails", action="store_true")
    pass_parser.add_argument("--skip-readiness", action="store_true")
    pass_parser.add_argument("--skip-artifact-index", action="store_true")
    pass_parser.add_argument("--skip-work-plan", action="store_true")
    pass_parser.add_argument("--skip-sync-pulse", action="store_true")
    pass_parser.add_argument("--skip-context-packet", action="store_true")
    pass_parser.add_argument(
        "--context-packet-agent-id",
        default="agent-harness-engineer",
    )
    pass_parser.add_argument("--export-memory-summary-to-obsidian", action="store_true")
    pass_parser.add_argument("--memory-summary-agent-id")
    pass_parser.add_argument("--memory-summary-limit", type=int, default=8)
    pass_parser.add_argument("--skip-skill-usage-ledger", action="store_true")
    pass_parser.add_argument("--skip-model-routing-ledger", action="store_true")
    pass_parser.add_argument("--skip-provider-smoke-ledger", action="store_true")
    pass_parser.add_argument("--provider-smoke-live", action="store_true")
    pass_parser.add_argument("--provider-smoke-realtime-provider")
    pass_parser.add_argument("--provider-smoke-voice")
    pass_parser.add_argument("--provider-smoke-search-query")
    pass_parser.add_argument("--skip-provider-ops-ledger", action="store_true")
    pass_parser.add_argument("--skip-realtime-dialogue-ledger", action="store_true")
    pass_parser.add_argument("--skip-feedback-resolution-ledger", action="store_true")
    pass_parser.add_argument("--skip-foundation-audit", action="store_true")
    pass_parser.add_argument("--skip-run-replay-ledger", action="store_true")
    pass_parser.add_argument("--generate-note", action="store_true")
    pass_parser.add_argument("--include-replay-event-payloads", action="store_true")
    pass_parser.add_argument("--disable-feedback-gate", action="store_true")
    pass_parser.add_argument("--disable-gemma", action="store_true")
    pass_parser.add_argument("--fail-on-provider-error", action="store_true")
    pass_parser.add_argument("--notes")
    resume_parser = subparsers.add_parser(
        "resume-run",
        help="Gate, checkpoint, and resume a durable run through worker execution.",
    )
    resume_parser.add_argument("--run-id", required=True)
    resume_parser.add_argument("--agent-id")
    resume_parser.add_argument("--worker-agent-id", action="append")
    resume_parser.add_argument("--max-tasks-per-agent", type=int, default=1)
    resume_parser.add_argument("--max-worker-rounds", type=int, default=1)
    resume_parser.add_argument("--skip-checkpoint", action="store_true")
    resume_parser.add_argument("--skip-work-plan", action="store_true")
    resume_parser.add_argument("--skip-followup-tasks", action="store_true")
    resume_parser.add_argument("--skip-active-profiles", action="store_true")
    resume_parser.add_argument("--skip-worker-cycle", action="store_true")
    resume_parser.add_argument("--disable-gemma", action="store_true")
    resume_parser.add_argument("--fail-on-provider-error", action="store_true")
    resume_parser.add_argument("--notes")
    sync_parser = subparsers.add_parser(
        "run-sync-pulse",
        help="Record a manager/scrum multi-agent sync pulse for a durable run.",
    )
    sync_parser.add_argument("--run-id", required=True)
    sync_parser.add_argument("--no-artifact", action="store_true")
    sync_parser.add_argument("--skip-work-plan", action="store_true")
    sync_parser.add_argument("--create-followup-tasks", action="store_true")
    sync_parser.add_argument("--include-completed-tasks", action="store_true")
    sync_parser.add_argument("--max-work-items", type=int, default=25)
    sync_parser.add_argument("--notes")
    runtime_parser = subparsers.add_parser(
        "build-runtime-health-ledger",
        help="Record Postgres, pgvector, Docker, LangGraph, and fallback-boundary runtime health for a durable run.",
    )
    runtime_parser.add_argument("--run-id", required=True)
    runtime_parser.add_argument("--event-limit", type=int, default=250)
    runtime_parser.add_argument("--skip-static-checks", action="store_true")
    runtime_parser.add_argument("--skip-run-evidence", action="store_true")
    runtime_parser.add_argument("--skip-live-store-evidence", action="store_true")
    runtime_parser.add_argument("--skip-voice-edge-benchmark", action="store_true")
    runtime_parser.add_argument("--no-artifact", action="store_true")
    provider_smoke_parser = subparsers.add_parser(
        "build-provider-smoke-ledger",
        help=(
            "Record run-level provider smoke proof for the selected realtime "
            "route, optional web search, local reranking, imagegen boundaries, "
            "and explicitly enabled legacy Gemma lanes."
        ),
    )
    provider_smoke_parser.add_argument("--run-id", required=True)
    provider_smoke_parser.add_argument(
        "--live",
        action="store_true",
        help="Call configured external providers instead of only recording readiness/blockers.",
    )
    provider_smoke_parser.add_argument(
        "--topic",
        default="provider smoke test for OpenRouter LiveKit content studio",
    )
    provider_smoke_parser.add_argument("--realtime-provider")
    provider_smoke_parser.add_argument("--voice")
    provider_smoke_parser.add_argument("--search-query")
    provider_smoke_parser.add_argument("--event-limit", type=int, default=250)
    provider_smoke_parser.add_argument("--skip-gemma", action="store_true")
    provider_smoke_parser.add_argument("--skip-realtime", action="store_true")
    provider_smoke_parser.add_argument("--skip-web-search", action="store_true")
    provider_smoke_parser.add_argument("--skip-reranker", action="store_true")
    provider_smoke_parser.add_argument("--skip-imagegen-boundary", action="store_true")
    provider_smoke_parser.add_argument("--no-artifact", action="store_true")
    walkthrough_parser = subparsers.add_parser(
        "build-cockpit-walkthrough-ledger",
        help=(
            "Record a run-level cockpit walkthrough proof packet covering "
            "runtime, provider readiness, source coverage, realtime smoke, "
            "provider observability, and feedback-loop state."
        ),
    )
    walkthrough_parser.add_argument("--run-id", required=True)
    walkthrough_parser.add_argument("--event-limit", type=int, default=250)
    walkthrough_parser.add_argument("--skip-runtime-health", action="store_true")
    walkthrough_parser.add_argument("--skip-static-runtime-checks", action="store_true")
    walkthrough_parser.add_argument("--skip-live-store-evidence", action="store_true")
    walkthrough_parser.add_argument("--no-artifact", action="store_true")
    voice_timing_parser = subparsers.add_parser(
        "build-realtime-voice-timing-ledger",
        help=(
            "Record measured LiveKit/OpenRouter/Kokoro voice-loop timing evidence "
            "from durable voice-agent events."
        ),
    )
    voice_timing_parser.add_argument("--run-id", required=True)
    voice_timing_parser.add_argument("--event-limit", type=int, default=500)
    voice_timing_parser.add_argument("--no-artifact", action="store_true")
    voice_capture_parser = subparsers.add_parser(
        "capture-livekit-voice-timing-proof",
        help=(
            "Join a provider-backed LiveKit realtime session headlessly, publish "
            "a synthetic audio probe, persist agent data-channel timing events, "
            "and optionally trigger barge-in cancellation."
        ),
    )
    voice_capture_parser.add_argument("--run-id", required=True)
    voice_capture_parser.add_argument("--realtime-session-id")
    voice_capture_parser.add_argument("--timeout-seconds", type=float, default=45.0)
    voice_capture_parser.add_argument(
        "--audio-probe-duration-ms",
        type=int,
        default=1200,
    )
    voice_capture_parser.add_argument(
        "--post-speech-silence-ms",
        type=int,
        default=900,
    )
    voice_capture_parser.add_argument(
        "--no-interrupt",
        action="store_true",
        help="Do not send a voice_interrupt control message after first output.",
    )
    voice_capture_parser.add_argument(
        "--transcript",
        help=(
            "Optional transcript_turn payload to send after joining. Leave unset "
            "when the proof must depend only on the published audio probe."
        ),
    )
    voice_capture_parser.add_argument("--voice")
    distribution_parser = subparsers.add_parser(
        "build-distribution-package",
        help="Create source-backed platform packaging for a durable run.",
    )
    distribution_parser.add_argument("--run-id", required=True)
    distribution_parser.add_argument("--platform", action="append")
    distribution_parser.add_argument(
        "--agent-id",
        default="platform-optimization-agent",
    )
    distribution_parser.add_argument(
        "--audience",
        default="AI-curious builders, creators, and operators",
    )
    distribution_parser.add_argument(
        "--campaign-goal",
        default="educate with source-backed, ELI5 content",
    )
    distribution_parser.add_argument("--skip-outreach", action="store_true")
    voice_agent_parser = subparsers.add_parser(
        "run-voice-agent",
        help=(
            "Run the LiveKit OpenRouter + Kokoro realtime voice agent server. "
            "Requires the voice optional dependencies and LiveKit/OpenRouter config."
        ),
    )
    voice_agent_parser.add_argument("--dev", action="store_true")
    voice_agent_parser.add_argument(
        "--unregistered",
        action="store_true",
        help="Start the agent server without registering with LiveKit.",
    )
    voice_benchmark_parser = subparsers.add_parser(
        "benchmark-voice-edge",
        help=(
            "Run a local synthetic VAD/barge-in latency and quality benchmark "
            "against the Rust voice-edge JSONL bridge or HTTP sidecar."
        ),
    )
    voice_benchmark_parser.add_argument("--binary-path")
    voice_benchmark_parser.add_argument(
        "--http-url",
        help=(
            "Benchmark an already-running Rust HTTP sidecar instead of the "
            "persistent JSONL subprocess."
        ),
    )
    voice_benchmark_parser.add_argument("--timeout-seconds", type=float)
    voice_benchmark_parser.add_argument(
        "--runs-per-scenario", type=_positive_int, default=5
    )
    voice_benchmark_parser.add_argument(
        "--samples-per-frame", type=_positive_int, default=512
    )
    voice_benchmark_parser.add_argument(
        "--speech-amplitude", type=_positive_int, default=2600
    )
    voice_benchmark_parser.add_argument(
        "--speech-wav",
        action="append",
        help=(
            "Use a local 16-bit PCM WAV speech fixture for speech/barge-in "
            "and concurrency probes instead of the synthetic constant-amplitude tone."
        ),
    )
    voice_benchmark_parser.add_argument(
        "--speech-wav-dir",
        action="append",
        help="Load all .wav speech fixtures from this project-relative directory.",
    )
    voice_benchmark_parser.add_argument(
        "--max-speech-frames",
        type=_benchmark_speech_frame_limit,
        default=64,
        help=(
            "Maximum voice-edge frames to use from --speech-wav "
            f"(<= {MAX_RUST_VOICE_EDGE_BENCHMARK_SPEECH_FRAMES})."
        ),
    )
    voice_benchmark_parser.add_argument(
        "--vad-backend",
        choices=["deterministic_energy", "silero_onnx"],
    )
    voice_benchmark_parser.add_argument("--vad-model-path")
    voice_benchmark_parser.add_argument("--no-vad-fallback", action="store_true")
    voice_benchmark_parser.add_argument("--vad-threshold", type=float)
    voice_benchmark_parser.add_argument("--vad-probability-threshold", type=float)
    voice_benchmark_parser.add_argument(
        "--vad-probability-threshold-sweep",
        type=_probability_thresholds,
        help="Comma-separated Silero probability thresholds to benchmark, e.g. 0.01,0.1,0.5.",
    )
    voice_benchmark_parser.add_argument("--vad-session-pool-size", type=_positive_int)
    voice_benchmark_parser.add_argument(
        "--vad-stream-state-cache-size", type=_positive_int
    )
    voice_benchmark_parser.add_argument("--min-speech-frames", type=_positive_int)
    voice_benchmark_parser.add_argument(
        "--concurrent-streams", type=_positive_int, default=4
    )
    voice_benchmark_parser.add_argument(
        "--concurrent-iterations", type=_positive_int, default=2
    )
    args = parser.parse_args()

    if args.command == "migrate":
        asyncio.run(_migrate())
    elif args.command == "setup-checkpointer":
        asyncio.run(_setup_checkpointer())
    elif args.command == "setup-durable-storage":
        asyncio.run(_setup_all())
    elif args.command == "blocker-credential-snapshot":
        _print_blocker_credential_snapshots(args)
    elif args.command == "provider-proof-plan":
        _print_provider_proof_plan(args)
    elif args.command == "validate-provider-proof-product-run-bootstrap":
        _print_provider_proof_product_run_bootstrap_validation(args)
    elif args.command == "init-provider-proof-workspace-from-bootstrap":
        _print_provider_proof_workspace_from_bootstrap(args)
    elif args.command == "provider-proof-record-template":
        _print_provider_proof_record_template(args)
    elif args.command == "init-provider-proof-workspace":
        _print_provider_proof_workspace(args)
    elif args.command == "validate-provider-proof-workspace":
        _print_provider_proof_workspace_validation(args)
    elif args.command == "provider-proof-operator-input-readiness":
        _print_provider_proof_operator_input_readiness(args)
    elif args.command == "validate-provider-proof-record":
        _print_provider_proof_record_validation(args)
    elif args.command == "validate-provider-proof-preflight-artifacts":
        _print_provider_proof_preflight_artifacts_validation(args)
    elif args.command == "record-provider-proof-record":
        _print_record_provider_proof_record(args)
    elif args.command == "provider-proof-completion-status":
        _print_provider_proof_completion_status(args)
    elif args.command == "provider-proof-closure-review-template":
        _print_provider_proof_closure_review_template(args)
    elif args.command == "validate-provider-proof-closure-review":
        _print_provider_proof_closure_review_validation(args)
    elif args.command == "record-provider-proof-closure-review":
        _print_record_provider_proof_closure_review(args)
    elif args.command == "provider-proof-closure-review-status":
        _print_provider_proof_closure_review_status(args)
    elif args.command == "record-provider-proof-blocker-state-update":
        _print_record_provider_proof_blocker_state_update(args)
    elif args.command == "provider-proof-current-blocker-matrix":
        _print_provider_proof_current_blocker_matrix(args)
    elif args.command == "provider-proof-current-status":
        _print_provider_proof_current_status(args)
    elif args.command == "provider-proof-operator-unblocker-checklist":
        _print_provider_proof_operator_unblocker_checklist(args)
    elif args.command == "run-agent-worker":
        asyncio.run(_run_agent_worker(args))
    elif args.command == "run-agent-cycle":
        asyncio.run(_run_agent_cycle(args))
    elif args.command == "run-worker-profile":
        asyncio.run(_run_worker_profile(args))
    elif args.command == "run-worker-scheduler":
        asyncio.run(_run_worker_scheduler(args))
    elif args.command == "run-autonomous-pass":
        asyncio.run(_run_autonomous_pass(args))
    elif args.command == "resume-run":
        asyncio.run(_resume_run(args))
    elif args.command == "run-sync-pulse":
        asyncio.run(_run_sync_pulse(args))
    elif args.command == "build-runtime-health-ledger":
        asyncio.run(_build_runtime_health_ledger(args))
    elif args.command == "build-provider-smoke-ledger":
        asyncio.run(_build_provider_smoke_ledger(args))
    elif args.command == "build-cockpit-walkthrough-ledger":
        asyncio.run(_build_cockpit_walkthrough_ledger(args))
    elif args.command == "build-realtime-voice-timing-ledger":
        asyncio.run(_build_realtime_voice_timing_ledger(args))
    elif args.command == "capture-livekit-voice-timing-proof":
        asyncio.run(_capture_livekit_voice_timing_proof(args))
    elif args.command == "build-distribution-package":
        asyncio.run(_build_distribution_package(args))
    elif args.command == "run-voice-agent":
        asyncio.run(_run_voice_agent(args))
    elif args.command == "benchmark-voice-edge":
        try:
            asyncio.run(_benchmark_voice_edge(args))
        except argparse.ArgumentTypeError as exc:
            parser.error(str(exc))


if __name__ == "__main__":
    main()
