#archivo será el encargado de transformar las contraseñas planas en hashes de Bcrypt.

import bcrypt


def get_password_hash(password: str) -> str:
    """Transforma la contraseña plana en un hash seguro (bcrypt)."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña ingresada coincide con el hash (bcrypt)."""
    plain_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hashed_bytes)