import os
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
import httpx

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Canvas OAuth"])

CANVAS_BASE = os.getenv("CANVAS_BASE_URL")
CLIENT_ID = os.getenv("CANVAS_CLIENT_ID")
CLIENT_SECRET = os.getenv("CANVAS_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")


@router.get("/canvas/login")
async def canvas_login():
    """Redirect the user to Canvas OAuth login page."""
    oauth_url = (
        f"{CANVAS_BASE}/login/oauth2/auth"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return RedirectResponse(oauth_url)


@router.get("/canvas/callback")
async def canvas_callback(request: Request, code: str):
    """Exchange Canvas OAuth code for an access token and return user info."""
    token_url = f"{CANVAS_BASE}/login/oauth2/token"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "code": code,
            },
        )

    if response.status_code != 200:
        return JSONResponse(status_code=400, content={"error": "Failed to get access token"})

    token_data = response.json()
    access_token = token_data.get("access_token")

    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            f"{CANVAS_BASE}/api/v1/users/self",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    user_info = user_resp.json()
    return {
        "message": "Canvas login successful ✅",
        "user_name": user_info.get("name"),
        "user_email": user_info.get("login_id"),
        "access_token": access_token[:10] + "...",  # partially hidden
    }
