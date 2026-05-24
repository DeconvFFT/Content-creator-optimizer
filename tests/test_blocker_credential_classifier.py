import json

from all_about_llms.orchestration.blocker_credentials import (
    BLOCKER_CREDENTIAL_ENV_NAMES,
    build_blocker_credential_snapshots,
)


PLACEHOLDER_ENV_NAMES = {
    "OPENROUTER_API_KEY",
    "OPENROUTER_LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "INSTAGRAM_ACCESS_TOKEN",
    "LINKEDIN_ACCESS_TOKEN",
    "X_ACCESS_TOKEN",
    "X_API_KEY",
    "SUBSTACK_API_TOKEN",
}

PUBLICATION_SECRET_FILE_ENV_NAMES = {
    "LINKEDIN_ACCESS_TOKEN_FILE",
}


def test_blocker_credential_classifier_reports_placeholder_only_state_without_values():
    snapshots = build_blocker_credential_snapshots(
        env_values={},
        placeholder_env_names=PLACEHOLDER_ENV_NAMES,
        checked_at="2026-05-20",
    )

    voice = snapshots["provider-backed-live-voice-proof"]
    assert voice["source"] == "non-secret local classifier"
    assert voice["state"] == "blocked_by_placeholder_only_configuration"
    assert voice["shell_values_loaded"] is False
    assert voice["secret_values_printed"] is False
    assert voice["placeholder_only_inputs"] == [
        "OPENROUTER_API_KEY",
        "OPENROUTER_LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
    ]
    assert voice["absent_inputs"] == ["LIVEKIT_URL"]

    publication = snapshots["external-publication-proof"]
    assert publication["state"] == "blocked_by_placeholder_only_configuration"
    assert publication["shell_values_loaded"] is False
    assert publication["secret_values_printed"] is False
    assert publication["placeholder_only_inputs"] == [
        "LINKEDIN_ACCESS_TOKEN",
    ]
    assert publication["absent_inputs"] == []


def test_blocker_credential_classifier_never_echoes_configured_secret_values():
    env_values = {
        "OPENROUTER_API_KEY": "openrouter_live_secret_value_that_must_not_echo",
        "OPENROUTER_LIVEKIT_URL": "wss://livekit.example",
        "LIVEKIT_API_KEY": "lk_key_that_must_not_echo",
        "LIVEKIT_API_SECRET": "lk_secret_that_must_not_echo",
        "LIVEKIT_URL": "wss://legacy_livekit_that_must_not_echo",
        "INSTAGRAM_ACCESS_TOKEN": "ig_secret_that_must_not_echo",
        "LINKEDIN_ACCESS_TOKEN": "li_secret_that_must_not_echo",
        "X_API_KEY": "x_secret_that_must_not_echo",
        "SUBSTACK_API_TOKEN": "substack_secret_that_must_not_echo",
    }

    snapshots = build_blocker_credential_snapshots(
        env_values=env_values,
        placeholder_env_names=PLACEHOLDER_ENV_NAMES,
        checked_at="2026-05-20",
    )
    serialized = json.dumps(snapshots)

    for secret_value in env_values.values():
        assert secret_value not in serialized

    voice = snapshots["provider-backed-live-voice-proof"]
    assert voice["state"] == "runtime_configuration_present_unverified"
    assert voice["shell_values_loaded"] is True
    assert voice["configured_inputs"] == BLOCKER_CREDENTIAL_ENV_NAMES[
        "provider-backed-live-voice-proof"
    ]
    assert voice["placeholder_only_inputs"] == []
    assert voice["absent_inputs"] == []
    assert "placeholder-only" not in voice["note"]
    assert "generic LIVEKIT_URL absent" not in voice["note"]
    assert voice["secret_values_printed"] is False

    publication = snapshots["external-publication-proof"]
    assert publication["state"] == "runtime_configuration_present_unverified"
    assert publication["shell_values_loaded"] is True
    assert publication["configured_inputs"] == [
        "LINKEDIN_ACCESS_TOKEN",
    ]
    assert publication["placeholder_only_inputs"] == []
    assert "placeholder-only" not in publication["note"]
    assert publication["secret_values_printed"] is False


def test_blocker_credential_classifier_reports_missing_required_configuration():
    snapshots = build_blocker_credential_snapshots(
        env_values={},
        placeholder_env_names={
            "OPENROUTER_API_KEY",
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET",
            "X_ACCESS_TOKEN",
            "SUBSTACK_API_TOKEN",
        },
        checked_at="2026-05-20",
    )

    voice = snapshots["provider-backed-live-voice-proof"]
    assert voice["state"] == "blocked_by_missing_configuration"
    assert "OPENROUTER_LIVEKIT_URL" in voice["absent_inputs"]
    assert "LIVEKIT_URL" in voice["absent_inputs"]

    publication = snapshots["external-publication-proof"]
    assert publication["state"] == "blocked_by_missing_configuration"
    assert publication["absent_inputs"] == ["LINKEDIN_ACCESS_TOKEN"]


def test_blocker_credential_classifier_accepts_secret_file_presence_without_values():
    snapshots = build_blocker_credential_snapshots(
        env_values={
            "OPENROUTER_LIVEKIT_URL": "wss://livekit.example",
        },
        placeholder_env_names=PLACEHOLDER_ENV_NAMES
        | {
            "OPENROUTER_API_KEY_FILE",
            "LIVEKIT_API_KEY_FILE",
            "LIVEKIT_API_SECRET_FILE",
        },
        configured_file_env_names={
            "OPENROUTER_API_KEY_FILE",
            "LIVEKIT_API_KEY_FILE",
            "LIVEKIT_API_SECRET_FILE",
        },
        checked_at="2026-05-20",
    )

    voice = snapshots["provider-backed-live-voice-proof"]
    assert voice["state"] == "runtime_configuration_present_unverified"
    assert voice["configured_inputs"] == [
        "OPENROUTER_LIVEKIT_URL",
    ]
    assert voice["configured_file_inputs"] == [
        "OPENROUTER_API_KEY_FILE",
        "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET_FILE",
    ]
    assert voice["placeholder_only_inputs"] == []
    assert voice["secret_files_loaded"] is True
    assert voice["secret_values_printed"] is False


def test_blocker_credential_classifier_accepts_publication_secret_files_without_values():
    snapshots = build_blocker_credential_snapshots(
        env_values={},
        placeholder_env_names=PLACEHOLDER_ENV_NAMES
        | PUBLICATION_SECRET_FILE_ENV_NAMES,
        configured_file_env_names={
            "LINKEDIN_ACCESS_TOKEN_FILE",
        },
        checked_at="2026-05-20",
    )

    publication = snapshots["external-publication-proof"]
    assert publication["state"] == "runtime_configuration_present_unverified"
    assert publication["shell_values_loaded"] is False
    assert publication["configured_inputs"] == []
    assert publication["configured_file_inputs"] == [
        "LINKEDIN_ACCESS_TOKEN_FILE",
    ]
    assert publication["placeholder_only_inputs"] == []
    assert publication["absent_inputs"] == []
    assert publication["secret_files_loaded"] is True
    assert publication["secret_values_printed"] is False
