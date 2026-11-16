"""Shared by every test module (pytest)."""
import pytest


@pytest.fixture(autouse=True)
def _a_signed_in_caller_for_new_recordings(request, monkeypatch):
    """Starting a NEW recording needs an access token (audio._signed_in_or_401). The audio tests
    call the routes as functions with a bare request, so they run as a signed-in caller; the rule
    itself is tested in test_auth_hardening."""
    if request.module.__name__.endswith("test_auth_hardening"):
        return
    from app.api.routers import audio

    monkeypatch.setattr(audio, "_signed_in_or_401", lambda _request: None)
