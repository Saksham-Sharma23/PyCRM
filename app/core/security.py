"""Password hashing.

We never store passwords, only a bcrypt hash. bcrypt is deliberately slow and
adds a random salt to every hash, so identical passwords produce different hashes
and leaked hashes are expensive to crack.
"""

import bcrypt

# bcrypt only uses the first 72 bytes of a password; longer input is rejected
# by the signup form (see app/schemas/user.py).
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    password_bytes = password.encode()
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return False  # could never have been set as a password
    return bcrypt.checkpw(password_bytes, password_hash.encode())
