from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth import router as auth_router
from app.canvas_api import get_user_profile, get_courses


app = FastAPI(title="Canvas AI Buddy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "Backend running successfully 🚀"}


@app.get("/me")
async def me():
    return await get_user_profile()

@app.get("/courses")
async def courses():
    return await get_courses()
