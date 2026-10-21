
import os
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import create_client
from supabase_auth.errors import AuthApiError

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise RuntimeError(
        "Set SUPABASE_URL and SUPABASE_KEY in your .env file"
    )

supabase = create_client(supabase_url, supabase_key)

app = FastAPI(
    title="BE-03 Auth: Login & Protect",
    description="Authentication API using Supabase Auth",
    version="1.0.0",
)

bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None or not credentials.credentials.strip():
        raise HTTPException(
            status_code=401,
            detail="Access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    try:
        response = supabase.auth.get_user(token)
        user = response.user

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

class AuthRequest(BaseModel):
    email: str | None = None
    password: str | None = None


@app.get("/public/info", tags=["Public"])
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile", tags=["Protected"])
def protected_profile(user=Depends(get_current_user)):
    return {
        "message": "You have accessed a protected route.",
        "profile": {
            "id": user.id,
            "email": user.email,
            "created_at": (
                user.created_at.isoformat()
                if user.created_at
                else None
            ),
        },
    }

@app.get("/protected/dashboard", tags=["Protected"])
def protected_dashboard(user=Depends(get_current_user)):
    return {
        "message": "Welcome to your protected dashboard.",
        "user": {
            "id": user.id,
            "email": user.email,
        },
    }

@app.post("/auth/signup", status_code=status.HTTP_201_CREATED, tags=["Auth"])
def signup(body: AuthRequest):
    if not body.email or not body.password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"},
        )

    try:
        response = supabase.auth.sign_up(
            {
                "email": body.email,
                "password": body.password,
            }
        )
        user = response.user

        if user is None:
            return JSONResponse(
                status_code=400,
                content={"error": "Signup could not be completed"},
            )

        return JSONResponse(
            status_code=201,
            content={
                "message": "User registered successfully",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "created_at": (
                        user.created_at.isoformat()
                        if user.created_at
                        else None
                    ),
                },
            },
        )

    except AuthApiError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": str(exc)},
        )


@app.post("/auth/login", tags=["Auth"])
def login(body: AuthRequest):
    if not body.email or not body.password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"},
        )

    try:
        response = supabase.auth.sign_in_with_password(
            {
                "email": body.email,
                "password": body.password,
            }
        )

        if response.session is None or response.user is None:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid login credentials"},
            )

        return {
            "message": "Login successful",
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": response.session.token_type,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
            },
        }

    except AuthApiError:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid login credentials"},
        )

@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["Auth"])
def logout(user=Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials.strip()

    try:
        response = httpx.post(
            f"{supabase_url.rstrip('/')}/auth/v1/logout",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {token}",
            },
            timeout=10.0,
        )

        if response.status_code not in (200, 204):
            raise HTTPException(
                status_code=401,
                detail="Logout failed",
            )

        return None

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Could not reach the authentication service",
        )