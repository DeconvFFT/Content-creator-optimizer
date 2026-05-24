import base64
import hashlib
import hmac


_CONTROL_BINDING_VERSION = "v1"


def build_livekit_control_binding_token(
    secret: str | None,
    *,
    run_id: str,
    realtime_session_id: str,
    room_name: str,
    participant_identity: str,
    agent_identity: str,
) -> str | None:
    if not secret:
        return None
    fields = [
        run_id,
        realtime_session_id,
        room_name,
        participant_identity,
        agent_identity,
    ]
    if any(not str(field).strip() for field in fields):
        return None
    digest = hmac.new(
        secret.encode("utf-8"),
        _control_binding_message(
            run_id=run_id,
            realtime_session_id=realtime_session_id,
            room_name=room_name,
            participant_identity=participant_identity,
            agent_identity=agent_identity,
        ).encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"{_CONTROL_BINDING_VERSION}.{signature}"


def verify_livekit_control_binding_token(
    token: object,
    secret: str | None,
    *,
    run_id: str,
    realtime_session_id: str,
    room_name: str,
    participant_identity: str,
    agent_identity: str,
) -> bool:
    if not isinstance(token, str) or not token.strip() or not secret:
        return False
    expected = build_livekit_control_binding_token(
        secret,
        run_id=run_id,
        realtime_session_id=realtime_session_id,
        room_name=room_name,
        participant_identity=participant_identity,
        agent_identity=agent_identity,
    )
    return bool(expected) and hmac.compare_digest(token, expected)


def _control_binding_message(
    *,
    run_id: str,
    realtime_session_id: str,
    room_name: str,
    participant_identity: str,
    agent_identity: str,
) -> str:
    return "\n".join(
        [
            _CONTROL_BINDING_VERSION,
            str(run_id),
            str(realtime_session_id),
            str(room_name),
            str(participant_identity),
            str(agent_identity),
        ]
    )
