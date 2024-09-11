from werkzeug.security import generate_password_hash, check_password_hash

def set_password(password):
    """Hashes the password using bcrypt."""
    return generate_password_hash(password)

def check_password(hashed_password, password):
    """Checks a hashed password."""
    return check_password_hash(hashed_password, password)
