from datetime import datetime, timedelta
from functools import lru_cache
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# =========================================================
# JWT Configuration
# =========================================================
SECRET_KEY = "smartinventorysupersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# =========================================================
# Password Hashing Configuration
# =========================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 Configuration (for Swagger UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# =========================================================
# Demo Users (replace later with DB)
# =========================================================
raw_users = {
    "admin": {"password": "admin123", "role": "admin"},
    "warehouse": {"password": "warehouse123", "role": "warehouse"},
}

# =========================================================
# Lazy Password Hashing (fixes bcrypt multiprocessing bug)
# =========================================================
@lru_cache()
def get_fake_users_db():
    """Hash passwords lazily when first accessed."""
    return {
        username: {
            "username": username,
            "hashed_password": pwd_context.hash(data["password"]),
            "role": data["role"],
        }
        for username, data in raw_users.items()
    }

# =========================================================
# Helper Functions
# =========================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain text password against hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str):
    """Validate username and password."""
    users = get_fake_users_db()
    user = users.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict):
    """Generate JWT token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str = Depends(oauth2_scheme)):
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def require_role(*roles):
    """Restrict route access to specific roles."""
    def role_checker(payload: dict = Depends(verify_token)):
        user_role = payload.get("role")
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Allowed roles: {roles}",
            )
        return payload
    return role_checker
