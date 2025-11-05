import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL")
ACCESS_TOKEN = os.getenv("CANVAS_ACCESS_TOKEN")


async def get_user_profile():
    """Fetch the authenticated user's Canvas profile information."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BASE_URL}/api/v1/users/self",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )
        res.raise_for_status()
        return res.json()


async def get_courses():
    """
    Return the user's favorite (starred) Canvas courses,
    as shown on their Canvas dashboard.
    """
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BASE_URL}/api/v1/users/self/favorites/courses",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )
        res.raise_for_status()
        favorite_courses = res.json()

    favorite_courses.sort(
        key=lambda c: c.get("term", {}).get("name", ""),
        reverse=True
    )
    return favorite_courses
