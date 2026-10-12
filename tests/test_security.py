from app.core.security import hash_password, verify_password


def test_hash_is_not_the_password_and_verifies():
    hashed = hash_password("password123")

    assert hashed != "password123"
    assert verify_password("password123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_same_password_gets_a_different_salt_each_time():
    assert hash_password("password123") != hash_password("password123")


def test_overlong_password_never_verifies():
    hashed = hash_password("password123")

    assert not verify_password("x" * 100, hashed)
