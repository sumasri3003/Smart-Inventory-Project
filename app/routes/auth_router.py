from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import authenticate_user, create_access_token, verify_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

# =========================================================
# LOGIN ENDPOINT
# =========================================================
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and return JWT token.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    token = create_access_token({
        "sub": user["username"],
        "role": user["role"]
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"]
    }

# =========================================================
# PROTECTED ENDPOINT
# =========================================================
@router.get("/protected")
def protected_route(payload: dict = Depends(verify_token)):
    """
    Example protected route that requires JWT authentication.
    """
    return {
        "message": f"Welcome {payload.get('sub')}! You are authorized 🎉",
        "role": payload.get("role")
    }
