"""Unit tests for the local_provider_config module – URL validation and sanitization."""

import pytest

from all_about_llms.local_provider_config import (
    LocalProviderConfigEnvName,
    LocalProviderConfigValidationError,
    is_default_local_provider_config_parent,
    local_provider_config_field_name,
    sanitized_local_provider_config_for_write,
    validate_local_provider_config_value,
    validated_managed_provider_config,
)
from pathlib import Path


# ─── validate_local_provider_config_value ────────────────────────────────────


class TestValidateLocalProviderConfigValue:
    def test_valid_https_endpoint_url(self):
        result = validate_local_provider_config_value(
            LocalProviderConfigEnvName.GEMMA4_MULTIMODAL_ENDPOINT_URL,
            "https://api.example.com/v1/completions",
        )
        assert result == "https://api.example.com/v1/completions"

    def test_valid_http_endpoint_url(self):
        result = validate_local_provider_config_value(
            LocalProviderConfigEnvName.GEMMA4_MULTIMODAL_ENDPOINT_URL,
            "http://localhost:8080/api",
        )
        assert result == "http://localhost:8080/api"

    def test_valid_wss_livekit_url(self):
        result = validate_local_provider_config_value(
            LocalProviderConfigEnvName.OPENROUTER_LIVEKIT_URL,
            "wss://livekit.example.com",
        )
        assert result == "wss://livekit.example.com"

    def test_valid_ws_livekit_url(self):
        result = validate_local_provider_config_value(
            LocalProviderConfigEnvName.GEMMA4_REALTIME_LIVEKIT_URL,
            "ws://localhost:7880",
        )
        assert result == "ws://localhost:7880"

    def test_livekit_url_allows_http(self):
        result = validate_local_provider_config_value(
            LocalProviderConfigEnvName.OPENROUTER_LIVEKIT_URL,
            "http://localhost:7880",
        )
        assert result == "http://localhost:7880"

    def test_blank_value_raises(self):
        with pytest.raises(LocalProviderConfigValidationError, match="cannot be blank"):
            validate_local_provider_config_value(
                LocalProviderConfigEnvName.GEMMA4_MULTIMODAL_ENDPOINT_URL,
                "   ",
            )

    def test_unsupported_env_name_raises(self):
        with pytest.raises(LocalProviderConfigValidationError, match="Unsupported"):
            validate_local_provider_config_value(
                "NOT_A_REAL_ENV_NAME",
                "https://example.com",
            )

    def test_non_http_endpoint_rejects_ws(self):
        with pytest.raises(LocalProviderConfigValidationError, match="http"):
            validate_local_provider_config_value(
                LocalProviderConfigEnvName.GEMMA4_MULTIMODAL_ENDPOINT_URL,
                "ws://example.com",
            )

    def test_rejects_credentials_in_url(self):
        with pytest.raises(LocalProviderConfigValidationError):
            validate_local_provider_config_value(
                LocalProviderConfigEnvName.GEMMA4_MULTIMODAL_ENDPOINT_URL,
                "https://user:pass@example.com/api",
            )

    def test_rejects_query_strings(self):
        with pytest.raises(LocalProviderConfigValidationError, match="query strings"):
            validate_local_provider_config_value(
                LocalProviderConfigEnvName.GEMMA4_MULTIMODAL_ENDPOINT_URL,
                "https://example.com/api?key=value",
            )

    def test_rejects_fragments(self):
        with pytest.raises(LocalProviderConfigValidationError, match="fragments"):
            validate_local_provider_config_value(
                LocalProviderConfigEnvName.GEMMA4_MULTIMODAL_ENDPOINT_URL,
                "https://example.com/api#section",
            )

    def test_rejects_no_host(self):
        with pytest.raises(LocalProviderConfigValidationError):
            validate_local_provider_config_value(
                LocalProviderConfigEnvName.GEMMA4_MULTIMODAL_ENDPOINT_URL,
                "not-a-url",
            )

    def test_strips_whitespace_from_value(self):
        result = validate_local_provider_config_value(
            LocalProviderConfigEnvName.GEMMA4_MULTIMODAL_ENDPOINT_URL,
            "  https://example.com/api  ",
        )
        assert result == "https://example.com/api"


# ─── validated_managed_provider_config ───────────────────────────────────────


class TestValidatedManagedProviderConfig:
    def test_valid_config_passes_through(self):
        config = {
            "GEMMA4_MULTIMODAL_ENDPOINT_URL": "https://example.com/v1",
            "OPENROUTER_LIVEKIT_URL": "wss://livekit.example.com",
        }
        result = validated_managed_provider_config(config)
        assert result["GEMMA4_MULTIMODAL_ENDPOINT_URL"] == "https://example.com/v1"
        assert result["OPENROUTER_LIVEKIT_URL"] == "wss://livekit.example.com"

    def test_invalid_values_silently_skipped(self):
        config = {
            "GEMMA4_MULTIMODAL_ENDPOINT_URL": "not-a-url",
            "OPENROUTER_LIVEKIT_URL": "wss://valid.com",
        }
        result = validated_managed_provider_config(config)
        assert "GEMMA4_MULTIMODAL_ENDPOINT_URL" not in result
        assert "OPENROUTER_LIVEKIT_URL" in result

    def test_non_string_values_skipped(self):
        config = {
            "GEMMA4_MULTIMODAL_ENDPOINT_URL": None,
            "OPENROUTER_LIVEKIT_URL": 12345,
        }
        result = validated_managed_provider_config(config)
        assert result == {}

    def test_empty_config(self):
        assert validated_managed_provider_config({}) == {}


# ─── sanitized_local_provider_config_for_write ───────────────────────────────


class TestSanitizedLocalProviderConfigForWrite:
    def test_preserves_unmanaged_keys(self):
        config = {
            "CUSTOM_KEY": "some_value",
            "GEMMA4_MULTIMODAL_ENDPOINT_URL": "https://example.com/v1",
        }
        result = sanitized_local_provider_config_for_write(config)
        assert result["CUSTOM_KEY"] == "some_value"
        assert result["GEMMA4_MULTIMODAL_ENDPOINT_URL"] == "https://example.com/v1"

    def test_invalid_managed_keys_removed_but_custom_preserved(self):
        config = {
            "CUSTOM_KEY": "keep_me",
            "GEMMA4_MULTIMODAL_ENDPOINT_URL": "not-valid",
        }
        result = sanitized_local_provider_config_for_write(config)
        assert result["CUSTOM_KEY"] == "keep_me"
        assert "GEMMA4_MULTIMODAL_ENDPOINT_URL" not in result


# ─── local_provider_config_field_name ────────────────────────────────────────


class TestLocalProviderConfigFieldName:
    def test_maps_env_to_field(self):
        assert (
            local_provider_config_field_name(
                LocalProviderConfigEnvName.GEMMA4_MULTIMODAL_ENDPOINT_URL
            )
            == "gemma4_multimodal_endpoint_url"
        )
        assert (
            local_provider_config_field_name(
                LocalProviderConfigEnvName.OPENROUTER_LIVEKIT_URL
            )
            == "openrouter_livekit_url"
        )


# ─── is_default_local_provider_config_parent ─────────────────────────────────


class TestIsDefaultLocalProviderConfigParent:
    def test_correct_parent(self):
        root = Path("/project")
        parent = root / ".secrets"
        assert is_default_local_provider_config_parent(root, parent) is True

    def test_incorrect_parent(self):
        root = Path("/project")
        parent = root / "config"
        assert is_default_local_provider_config_parent(root, parent) is False
