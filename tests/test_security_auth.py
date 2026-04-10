import asyncio
from datetime import datetime, timedelta, timezone

from app.core.security import get_password_hash, verify_password
from app.services.auth import AuthService
import app.services.auth as auth_module


class DummyUser:
    def __init__(self, password: str, auth_provider: str = "local") -> None:
        self.email = "student@example.com"
        self.password = password
        self.auth_provider = auth_provider
        self.saved = False

    async def save(self) -> None:
        self.saved = True


def test_password_hash_and_verify_roundtrip() -> None:
    password = "StrongPass123"
    hashed = get_password_hash(password)

    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password(password, hashed)
    assert not verify_password("wrong-pass", hashed)


def test_verify_password_legacy_plaintext_compatibility() -> None:
    assert verify_password("abc12345", "abc12345")
    assert not verify_password("wrong", "abc12345")


def test_authenticate_user_migrates_plaintext_password(monkeypatch) -> None:
    dummy = DummyUser(password="legacy-pass")

    class FakeUserModel:
        email = object()

    async def fake_find_one(*_args, **_kwargs):
        return dummy

    FakeUserModel.find_one = staticmethod(fake_find_one)
    monkeypatch.setattr(auth_module, "User", FakeUserModel)

    result = asyncio.run(AuthService.authenticate_user("student@example.com", "legacy-pass"))

    assert result is dummy
    assert dummy.saved is True
    assert dummy.password.startswith("pbkdf2_sha256$")


def test_authenticate_user_rejects_invalid_password(monkeypatch) -> None:
    hashed = get_password_hash("CorrectPass123")
    dummy = DummyUser(password=hashed)

    class FakeUserModel:
        email = object()

    async def fake_find_one(*_args, **_kwargs):
        return dummy

    FakeUserModel.find_one = staticmethod(fake_find_one)
    monkeypatch.setattr(auth_module, "User", FakeUserModel)

    result = asyncio.run(AuthService.authenticate_user("student@example.com", "WrongPass"))

    assert result is None
    assert dummy.saved is False


def test_request_password_reset_unknown_email_is_silent(monkeypatch) -> None:
    class FakeUserModel:
        email = object()

    async def fake_find_one(*_args, **_kwargs):
        return None

    async def fake_send_password_reset_email(*_args, **_kwargs):
        raise AssertionError("send_password_reset_email should not be called for unknown emails")

    FakeUserModel.find_one = staticmethod(fake_find_one)
    monkeypatch.setattr(auth_module, "User", FakeUserModel)
    monkeypatch.setattr(auth_module, "send_password_reset_email", fake_send_password_reset_email)

    asyncio.run(
        AuthService.request_password_reset(
            "missing@example.com",
            lambda token: f"https://example.com/auth/reset-password?token={token}",
        )
    )


def test_reset_password_with_token_updates_password_and_clears_reset_fields(monkeypatch) -> None:
    class ResettableUser:
        def __init__(self) -> None:
            self.email = "student@example.com"
            self.password = "legacy"
            self.auth_provider = "local"
            self.password_reset_token_hash = "token-hash"
            self.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
            self.saved = False

        async def save(self) -> None:
            self.saved = True

    dummy = ResettableUser()

    async def fake_validate_reset_token(_token: str):
        return dummy

    monkeypatch.setattr(AuthService, "validate_reset_token", staticmethod(fake_validate_reset_token))

    success = asyncio.run(AuthService.reset_password_with_token("valid-token", "NewPass123"))

    assert success is True
    assert dummy.saved is True
    assert dummy.password_reset_token_hash is None
    assert dummy.password_reset_expires_at is None
    assert dummy.password.startswith("pbkdf2_sha256$")
    assert verify_password("NewPass123", dummy.password)


def test_validate_reset_token_handles_naive_datetime(monkeypatch) -> None:
    class ResettableUser:
        def __init__(self) -> None:
            self.password_reset_token_hash = "token-hash"
            self.password_reset_expires_at = datetime.utcnow() + timedelta(minutes=15)
            self.saved = False

        async def save(self) -> None:
            self.saved = True

    dummy = ResettableUser()

    class FakeUserModel:
        password_reset_token_hash = object()

    async def fake_find_one(*_args, **_kwargs):
        return dummy

    FakeUserModel.find_one = staticmethod(fake_find_one)
    monkeypatch.setattr(auth_module, "User", FakeUserModel)
    monkeypatch.setattr(AuthService, "_hash_reset_token", staticmethod(lambda _token: "token-hash"))

    result = asyncio.run(AuthService.validate_reset_token("preview-token"))

    assert result is dummy
    assert dummy.saved is False
