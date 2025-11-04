import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL")
ACCESS_TOKEN = os.getenv("CANVAS_ACCESS_TOKEN")

async def get_user_profile():
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{BASE_URL}/api/v1/users/self", headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        })
        return res.json()

async def get_courses():
    """
    Returns only courses that appear on the user's Canvas Dashboard:
    - Enrollment is active (student or TA)
    - Course is published
    - Handles pagination
    - Sorted by creation date (latest first)
    """
    all_courses = []
    params = {
        "enrollment_type": ["student", "ta"],
        "enrollment_state": "active",
        "state[]": ["available"],
        "include[]": ["term", "total_students", "teachers"],
        "per_page": 100
    }

async def get_courses():
    """
    Returns only the user's FAVORITE (starred) Canvas courses —
    exactly what appears on their dashboard.
    """
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BASE_URL}/api/v1/users/self/favorites/courses",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )
        res.raise_for_status()
        favorite_courses = res.json()

    # Sort newest term first
    favorite_courses.sort(
        key=lambda c: c.get("term", {}).get("name", ""),
        reverse=True
    )

    return favorite_courses
       