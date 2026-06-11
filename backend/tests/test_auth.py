import pytest
from app.routers.auth import _hash_password, _verify_password


def test_hash_password_generates_valid_hash():
    password = "supersecretpassword123"
    hashed = _hash_password(password)
    
    assert hashed != password
    assert len(hashed) > 0
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")  # Valid bcrypt prefix


def test_verify_password_correct():
    password = "mypassword"
    hashed = _hash_password(password)
    
    assert _verify_password(password, hashed) is True


def test_verify_password_incorrect():
    password = "mypassword"
    hashed = _hash_password(password)
    
    assert _verify_password("wrongpassword", hashed) is False


def test_unicode_passwords():
    password = "ñandú_123_🔥"
    hashed = _hash_password(password)
    
    assert _verify_password(password, hashed) is True
    assert _verify_password("nandu_123_🔥", hashed) is False
