import json
from argparse import Namespace

from all_about_llms.cli import _blocker_credential_snapshot_payload


def test_blocker_credential_snapshot_cli_payload_uses_env_example_names(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "# placeholders",
                "OPENROUTER_API_KEY=",
                "OPENROUTER_LIVEKIT_URL=ws://127.0.0.1:7880",
                "LIVEKIT_API_KEY=",
                "LIVEKIT_API_SECRET=",
                "INSTAGRAM_ACCESS_TOKEN=",
                "LINKEDIN_ACCESS_TOKEN=",
                "X_ACCESS_TOKEN=",
                "X_API_KEY=",
                "SUBSTACK_API_TOKEN=",
            ]
        )
    )

    payload = _blocker_credential_snapshot_payload(
        Namespace(env_example_path=env_example, checked_at="2026-05-20"),
        env_values={},
    )

    assert payload["artifact"] == "agent-studio-blocker-credential-snapshots"
    assert payload["boundary"] == "no_secret_values_printed"
    voice = payload["snapshots"]["provider-backed-live-voice-proof"]
    assert voice["state"] == "blocked_by_placeholder_only_configuration"
    assert voice["secret_values_printed"] is False
    assert "LIVEKIT_URL" in voice["absent_inputs"]


def test_blocker_credential_snapshot_cli_payload_never_echoes_secret_values(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY=",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY=",
                "LIVEKIT_API_SECRET=",
                "INSTAGRAM_ACCESS_TOKEN=",
                "LINKEDIN_ACCESS_TOKEN=",
                "X_API_KEY=",
                "SUBSTACK_API_TOKEN=",
            ]
        )
    )
    env_values = {
        "OPENROUTER_API_KEY": "openrouter_secret_cli_test_must_not_echo",
        "OPENROUTER_LIVEKIT_URL": "wss://livekit.example",
        "LIVEKIT_API_KEY": "livekit_key_cli_test_must_not_echo",
        "LIVEKIT_API_SECRET": "livekit_secret_cli_test_must_not_echo",
        "INSTAGRAM_ACCESS_TOKEN": "instagram_cli_test_must_not_echo",
        "LINKEDIN_ACCESS_TOKEN": "linkedin_cli_test_must_not_echo",
        "X_API_KEY": "x_cli_test_must_not_echo",
        "SUBSTACK_API_TOKEN": "substack_cli_test_must_not_echo",
    }

    payload = _blocker_credential_snapshot_payload(
        Namespace(env_example_path=env_example, checked_at="2026-05-20"),
        env_values=env_values,
    )
    serialized = json.dumps(payload)

    for secret_value in env_values.values():
        assert secret_value not in serialized
    assert payload["snapshots"]["provider-backed-live-voice-proof"]["state"] == (
        "runtime_configuration_present_unverified"
    )
    assert payload["snapshots"]["external-publication-proof"]["state"] == (
        "runtime_configuration_present_unverified"
    )


def test_blocker_credential_snapshot_cli_detects_secret_files_without_reading_values(
    tmp_path,
):
    secrets_dir = tmp_path / ".secrets"
    secrets_dir.mkdir()
    (secrets_dir / "openrouter_api_key").write_text(
        "openrouter_file_secret_cli_test_must_not_echo\n",
        encoding="utf-8",
    )
    (secrets_dir / "livekit_api_key").write_text(
        "livekit_file_key_cli_test_must_not_echo\n",
        encoding="utf-8",
    )
    (secrets_dir / "livekit_api_secret").write_text(
        "livekit_file_secret_cli_test_must_not_echo\n",
        encoding="utf-8",
    )
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY=",
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET=",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
            ]
        )
    )

    payload = _blocker_credential_snapshot_payload(
        Namespace(env_example_path=env_example, checked_at="2026-05-20"),
        env_values={
            "OPENROUTER_LIVEKIT_URL": "wss://livekit.example",
        },
    )
    serialized = json.dumps(payload)

    assert "openrouter_file_secret_cli_test_must_not_echo" not in serialized
    assert "livekit_file_key_cli_test_must_not_echo" not in serialized
    assert "livekit_file_secret_cli_test_must_not_echo" not in serialized
    voice = payload["snapshots"]["provider-backed-live-voice-proof"]
    assert voice["state"] == "runtime_configuration_present_unverified"
    assert voice["configured_file_inputs"] == [
        "OPENROUTER_API_KEY_FILE",
        "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET_FILE",
    ]
    assert voice["secret_files_loaded"] is True


def test_blocker_credential_snapshot_cli_does_not_require_publication_tokens(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")

    payload = _blocker_credential_snapshot_payload(
        Namespace(env_example_path=env_example, checked_at="2026-05-20"),
        env_values={},
    )

    serialized = json.dumps(payload)
    publication = payload["snapshots"]["external-publication-proof"]
    assert publication["state"] == "runtime_configuration_present_unverified"
    assert publication["configured_inputs"] == []
    assert publication["configured_file_inputs"] == []
    assert "LINKEDIN_ACCESS_TOKEN_FILE" not in serialized
