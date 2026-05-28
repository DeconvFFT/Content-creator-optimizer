"""Unit tests for the realtime_safety module -- redaction and metadata sanitization."""

import pytest

from all_about_llms.realtime_safety import (
    normalize_realtime_metadata_key,
    realtime_metadata_key_is_sensitive,
    redact_realtime_string,
    safe_realtime_metadata,
    safe_realtime_metadata_value,
)


class TestRedactRealtimeString:
    def test_redacts_bearer_token(self):
        token_value = "tok123456789abcdefgh"
        raw = "Authorization: Bearer " + token_value
        result = redact_realtime_string(raw)
        assert "[redacted]" in result
        assert token_value not in result

    def test_redacts_bearer_case_insensitive(self):
        token_value = "abc123longtoken.xyz"
        raw = f"BEARER {token_value}"
        result = redact_realtime_string(raw)
        assert "[redacted]" in result
        assert token_value not in result

    def test_redacts_hf_token(self):
        raw = "token=hf_abcdefghijklmnopqrstuvwxyz"
        result = redact_realtime_string(raw)
        assert "hf_[redacted]" in result
        assert "hf_abcdefghijklmnopqrstuvwxyz" not in result

    def test_redacts_tavily_token(self):
        raw = "key=tvly-abcdefghijklmnopqrstuvwxyz"
        result = redact_realtime_string(raw)
        assert "tvly-[redacted]" in result
        assert "tvly-abcdefghijklmnopqrstuvwxyz" not in result

    def test_preserves_non_sensitive_text(self):
        raw = "Hello world, no secrets here"
        assert redact_realtime_string(raw) == raw

    def test_multiple_secrets_in_one_string(self):
        token_value = "tok123456789abcdef"
        raw = "Bearer " + token_value + " and hf_yyyyyyyyyyyyyyyyyyyyyyy"
        result = redact_realtime_string(raw)
        assert "[redacted]" in result
        assert "hf_[redacted]" in result
        assert token_value not in result
        assert "hf_yy" not in result

    def test_empty_string(self):
        assert redact_realtime_string("") == ""

    def test_bearer_with_special_characters(self):
        # Characters in [A-Za-z0-9._~+/=-] are part of the token pattern
        token_value = "abc.xyz_123~456"
        raw = f"bearer {token_value}"
        result = redact_realtime_string(raw)
        assert "[redacted]" in result
        assert token_value not in result


class TestNormalizeRealtimeMetadataKey:
    def test_snake_case_passthrough(self):
        assert normalize_realtime_metadata_key("access_token") == "access_token"

    def test_camel_case_split(self):
        assert normalize_realtime_metadata_key("accessToken") == "access_token"

    def test_upper_camel_case(self):
        assert normalize_realtime_metadata_key("ApiKey") == "api_key"

    def test_leading_trailing_whitespace(self):
        assert normalize_realtime_metadata_key("  accessToken  ") == "access_token"

    def test_special_characters_become_underscore(self):
        assert normalize_realtime_metadata_key("api-key") == "api_key"
        assert normalize_realtime_metadata_key("api.key") == "api_key"


class TestRealtimeMetadataKeyIsSensitive:
    @pytest.mark.parametrize(
        "key",
        [
            "access_token",
            "api_key",
            "api_secret",
            "authorization",
            "client_secret",
            "private_key",
            "refresh_token",
            "session_token",
            "livekit_token",
            "websocket_url",
            "token",
            "binding_token",
            "control_binding_token",
            "control_binding_signature",
        ],
    )
    def test_known_sensitive_keys(self, key):
        assert realtime_metadata_key_is_sensitive(key) is True

    @pytest.mark.parametrize(
        "key",
        [
            "control_binding_required",
            "control_binding_token_issued",
            "has_token",
            "has_transport_token",
            "livekit_token_expires_at_unix",
            "token_persisted",
        ],
    )
    def test_safe_exact_keys_not_sensitive(self, key):
        assert realtime_metadata_key_is_sensitive(key) is False

    def test_camel_case_sensitive_key(self):
        assert realtime_metadata_key_is_sensitive("accessToken") is True
        assert realtime_metadata_key_is_sensitive("apiKey") is True

    def test_suffix_based_sensitivity(self):
        assert realtime_metadata_key_is_sensitive("my_custom_key") is True
        assert realtime_metadata_key_is_sensitive("webhook_secret") is True
        assert realtime_metadata_key_is_sensitive("auth_token") is True
        assert realtime_metadata_key_is_sensitive("db_password") is True

    def test_non_string_key(self):
        assert realtime_metadata_key_is_sensitive(123) is False
        assert realtime_metadata_key_is_sensitive(None) is False

    def test_empty_string(self):
        assert realtime_metadata_key_is_sensitive("") is False
        assert realtime_metadata_key_is_sensitive("   ") is False

    def test_contains_authorization(self):
        assert realtime_metadata_key_is_sensitive("custom_authorization_header") is True

    def test_contains_bearer(self):
        assert realtime_metadata_key_is_sensitive("bearer_info") is True

    def test_contains_credential(self):
        assert realtime_metadata_key_is_sensitive("user_credential_hash") is True

    def test_non_sensitive_normal_key(self):
        assert realtime_metadata_key_is_sensitive("model_id") is False
        assert realtime_metadata_key_is_sensitive("run_id") is False
        assert realtime_metadata_key_is_sensitive("status") is False


class TestSafeRealtimeMetadata:
    def test_removes_sensitive_keys(self):
        metadata = {
            "model_id": "gemma-4",
            "access_token": "secret123",
            "run_id": "abc",
        }
        result = safe_realtime_metadata(metadata)
        assert "access_token" not in result
        assert result["model_id"] == "gemma-4"
        assert result["run_id"] == "abc"

    def test_preserves_none_token_value(self):
        metadata = {"token": None}
        result = safe_realtime_metadata(metadata)
        assert result == {"token": None}

    def test_redacts_strings_in_non_sensitive_values(self):
        metadata = {"info": "use hf_abcdefghijklmnopqrstu token here"}
        result = safe_realtime_metadata(metadata)
        assert "hf_[redacted]" in result["info"]
        assert "hf_abcdefghijklmnopqrstu" not in result["info"]

    def test_nested_dict_sanitized(self):
        metadata = {
            "outer": {
                "api_key": "should_be_removed",
                "name": "safe_value",
            }
        }
        result = safe_realtime_metadata(metadata)
        assert "api_key" not in result["outer"]
        assert result["outer"]["name"] == "safe_value"

    def test_empty_metadata(self):
        assert safe_realtime_metadata({}) == {}


class TestSafeRealtimeMetadataValue:
    def test_dict_recurses(self):
        value = {"api_key": "secret", "name": "test"}
        result = safe_realtime_metadata_value(value)
        assert "api_key" not in result
        assert result["name"] == "test"

    def test_list_maps_items(self):
        value = ["hf_abcdefghijklmnopqrstu", "hello"]
        result = safe_realtime_metadata_value(value)
        assert "hf_[redacted]" in result[0]
        assert result[1] == "hello"

    def test_string_redaction(self):
        assert "hf_[redacted]" in safe_realtime_metadata_value(
            "hf_12345678901234567890"
        )

    def test_int_passthrough(self):
        assert safe_realtime_metadata_value(42) == 42

    def test_none_passthrough(self):
        assert safe_realtime_metadata_value(None) is None

    def test_bool_passthrough(self):
        assert safe_realtime_metadata_value(True) is True
