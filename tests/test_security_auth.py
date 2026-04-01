import asyncio

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
