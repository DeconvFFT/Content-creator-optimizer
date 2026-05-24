import re
from collections.abc import Iterable, Mapping


BLOCKER_CREDENTIAL_ENV_NAMES = {
    "provider-backed-live-voice-proof": [
        "OPENROUTER_API_KEY",
        "OPENROUTER_LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
    ],
    "external-publication-proof": [
        "INSTAGRAM_ACCESS_TOKEN",
        "LINKEDIN_ACCESS_TOKEN",
        "X_ACCESS_TOKEN",
        "X_API_KEY",
        "SUBSTACK_API_TOKEN",
    ],
}

BLOCKER_SECRET_FILE_ENV_NAMES = {
    "provider-backed-live-voice-proof": {
        "OPENROUTER_API_KEY": "OPENROUTER_API_KEY_FILE",
        "LIVEKIT_API_KEY": "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET": "LIVEKIT_API_SECRET_FILE",
    },
    "external-publication-proof": {
        "INSTAGRAM_ACCESS_TOKEN": "INSTAGRAM_ACCESS_TOKEN_FILE",
        "LINKEDIN_ACCESS_TOKEN": "LINKEDIN_ACCESS_TOKEN_FILE",
        "X_ACCESS_TOKEN": "X_ACCESS_TOKEN_FILE",
        "X_API_KEY": "X_API_KEY_FILE",
        "SUBSTACK_API_TOKEN": "SUBSTACK_API_TOKEN_FILE",
    },
}

_BLOCKER_GROUPS = {
    "provider-backed-live-voice-proof": [
        ("OPENROUTER_API_KEY",),
        ("OPENROUTER_LIVEKIT_URL",),
        ("LIVEKIT_API_KEY",),
        ("LIVEKIT_API_SECRET",),
    ],
    "external-publication-proof": [
        ("INSTAGRAM_ACCESS_TOKEN",),
        ("LINKEDIN_ACCESS_TOKEN",),
        ("X_ACCESS_TOKEN", "X_API_KEY"),
        ("SUBSTACK_API_TOKEN",),
    ],
}

_NON_REQUIRED_ABSENCE_NOTES = {
    "provider-backed-live-voice-proof": ["LIVEKIT_URL"],
    "external-publication-proof": [],
}

_PLACEHOLDER_CREDENTIAL_VALUE_PATTERN = re.compile(r"^<[^>\n]+>$")

def build_blocker_credential_snapshots(
    *,
    env_values: Mapping[str, str | None],
    placeholder_env_names: Iterable[str] = (),
    configured_file_env_names: Iterable[str] = (),
    configured_local_provider_env_names: Iterable[str] = (),
    checked_at: str,
) -> dict[str, dict[str, object]]:
    """Build blocker credential snapshots without copying secret values."""

    placeholder_names = set(placeholder_env_names)
    configured_file_names = set(configured_file_env_names)
    configured_local_provider_names = set(configured_local_provider_env_names)
    return {
        blocker_id: _snapshot_for_blocker(
            blocker_id=blocker_id,
            env_values=env_values,
            placeholder_names=placeholder_names,
            configured_file_names=configured_file_names,
            configured_local_provider_names=configured_local_provider_names,
            checked_at=checked_at,
        )
        for blocker_id in BLOCKER_CREDENTIAL_ENV_NAMES
    }


def _snapshot_for_blocker(
    *,
    blocker_id: str,
    env_values: Mapping[str, str | None],
    placeholder_names: set[str],
    configured_file_names: set[str],
    configured_local_provider_names: set[str],
    checked_at: str,
) -> dict[str, object]:
    env_names = BLOCKER_CREDENTIAL_ENV_NAMES[blocker_id]
    file_env_by_env = BLOCKER_SECRET_FILE_ENV_NAMES[blocker_id]
    configured_inputs = [
        env_name for env_name in env_names if _has_nonempty_value(env_values, env_name)
    ]
    configured_file_inputs = [
        file_env
        for env_name in env_names
        if (file_env := file_env_by_env.get(env_name))
        and file_env in configured_file_names
    ]
    configured_local_provider_inputs = [
        env_name for env_name in env_names if env_name in configured_local_provider_names
    ]
    configured_env_names = {
        env_name
        for env_name in env_names
        if _is_configured(
            env_values=env_values,
            env_name=env_name,
            file_env_by_env=file_env_by_env,
            configured_file_names=configured_file_names,
            configured_local_provider_names=configured_local_provider_names,
        )
    }
    placeholder_only_inputs = [
        env_name
        for env_name in env_names
        if env_name in placeholder_names and env_name not in configured_env_names
    ]
    required_groups_satisfied = all(
        any(
            _is_configured(
                env_values=env_values,
                env_name=env_name,
                file_env_by_env=file_env_by_env,
                configured_file_names=configured_file_names,
                configured_local_provider_names=configured_local_provider_names,
            )
            for env_name in group
        )
        for group in _BLOCKER_GROUPS[blocker_id]
    )
    absent_required_inputs = _absent_required_inputs(
        blocker_id=blocker_id,
        env_values=env_values,
        placeholder_names=placeholder_names,
        configured_file_names=configured_file_names,
        configured_local_provider_names=configured_local_provider_names,
    )
    absent_inputs = absent_required_inputs + [
        env_name
        for env_name in _NON_REQUIRED_ABSENCE_NOTES[blocker_id]
        if not _has_nonempty_value(env_values, env_name)
        and env_name not in placeholder_names
    ]
    state = (
        "runtime_configuration_present_unverified"
        if required_groups_satisfied
        else "blocked_by_missing_configuration"
        if absent_required_inputs
        else "blocked_by_placeholder_only_configuration"
    )

    return {
        "source": "non-secret local classifier",
        "checked_at": checked_at,
        "state": state,
        "shell_values_loaded": bool(configured_inputs),
        "secret_files_loaded": bool(configured_file_inputs),
        "secret_values_printed": False,
        "configured_inputs": configured_inputs,
        "configured_file_inputs": configured_file_inputs,
        "configured_local_provider_inputs": configured_local_provider_inputs,
        "local_provider_config_loaded": bool(configured_local_provider_inputs),
        "placeholder_only_inputs": placeholder_only_inputs,
        "absent_inputs": absent_inputs,
        "note": _note_for_snapshot(
            blocker_id=blocker_id,
            state=state,
            absent_inputs=absent_inputs,
        ),
    }


def _note_for_snapshot(
    *,
    blocker_id: str,
    state: str,
    absent_inputs: list[str],
) -> str:
    if state == "runtime_configuration_present_unverified":
        if blocker_id == "provider-backed-live-voice-proof":
            return (
                "Runtime configuration names are present but unverified; "
                "same-session OpenRouter/Kokoro/LiveKit proof is still required."
            )
        return (
            "Runtime configuration names are present but unverified; exact "
            "destination publication proof is still required."
        )

    if state == "blocked_by_missing_configuration":
        return (
            "Required credential names are missing from both runtime "
            "environment and placeholder coverage."
        )

    if blocker_id == "provider-backed-live-voice-proof":
        note = (
            "placeholder-only .env.example entries for the canonical "
            "LiveKit/OpenRouter/Kokoro inputs"
        )
        if "LIVEKIT_URL" in absent_inputs:
            note += "; generic LIVEKIT_URL absent"
        return f"{note}."

    return (
        "placeholder-only .env.example entries for the requested external "
        "publication credentials."
    )


def _absent_required_inputs(
    *,
    blocker_id: str,
    env_values: Mapping[str, str | None],
    placeholder_names: set[str],
    configured_file_names: set[str],
    configured_local_provider_names: set[str],
) -> list[str]:
    absent_inputs: list[str] = []
    file_env_by_env = BLOCKER_SECRET_FILE_ENV_NAMES[blocker_id]
    for group in _BLOCKER_GROUPS[blocker_id]:
        if any(
            _is_configured(
                env_values=env_values,
                env_name=env_name,
                file_env_by_env=file_env_by_env,
                configured_file_names=configured_file_names,
                configured_local_provider_names=configured_local_provider_names,
            )
            for env_name in group
        ):
            continue
        if any(
            env_name in placeholder_names
            or file_env_by_env.get(env_name) in placeholder_names
            for env_name in group
        ):
            continue
        absent_inputs.extend(
            env_name for env_name in group if env_name not in placeholder_names
        )
    return absent_inputs


def _is_configured(
    *,
    env_values: Mapping[str, str | None],
    env_name: str,
    file_env_by_env: Mapping[str, str],
    configured_file_names: set[str],
    configured_local_provider_names: set[str],
) -> bool:
    file_env_name = file_env_by_env.get(env_name)
    return (
        _has_nonempty_value(env_values, env_name)
        or (file_env_name is not None and file_env_name in configured_file_names)
        or env_name in configured_local_provider_names
    )


def _has_nonempty_value(env_values: Mapping[str, str | None], env_name: str) -> bool:
    value = env_values.get(env_name)
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return bool(stripped) and not _PLACEHOLDER_CREDENTIAL_VALUE_PATTERN.fullmatch(
        stripped
    )
