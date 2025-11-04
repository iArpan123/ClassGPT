from fastapi import APIRouter, HTTPException
import os, httpx, traceback
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
BASE_URL = os.getenv("CANVAS_BASE_URL")
ACCESS_TOKEN = os.getenv("CANVAS_ACCESS_TOKEN")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
PINECONE_HOST = os.getenv("PINECONE_HOST")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@router.post("/ingest/{course_id}")
async def ingest_course(course_id: int):
    try:
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

        async with httpx.AsyncClient() as http:
            # Fetch syllabus
            course_res = await http.get(
                f"{BASE_URL}/api/v1/courses/{course_id}",
                headers=headers,
                params={"include[]": "syllabus_body"},
            )
            course = course_res.json()
            syllabus = course.get("syllabus_body", "")
            course_name = course.get("name", "Unknown Course")

            # Fetch assignments
            assignments_res = await http.get(
                f"{BASE_URL}/api/v1/courses/{course_id}/assignments",
                headers=headers,
                params={"per_page": 100},
            )
            assignments = assignments_res.json()

            # Fetch announcements
            announcements_res = await http.get(
                f"{BASE_URL}/api/v1/announcements",
                headers=headers,
                params={"context_codes[]": f"course_{course_id}", "per_page": 50},
            )
            announcements = announcements_res.json()

            # Fetch discussions
            discussions_res = await http.get(
                f"{BASE_URL}/api/v1/courses/{course_id}/discussion_topics",
                headers=headers,
                params={"per_page": 50},
            )
            discussions = discussions_res.json()

        # 🧩 Prepare chunks for embedding
        text_chunks = []
        if syllabus:
            text_chunks.append(f"Syllabus: {syllabus}")

        for a in assignments:
            text_chunks.append(
                f"Assignment: {a.get('name')} | Due: {a.get('due_at')} | "
                f"Points: {a.get('points_possible')} | Description: {a.get('description', '')}"
            )

        for a in announcements:
            text_chunks.append(
                f"Announcement: {a.get('title')} | Date: {a.get('posted_at')} | "
                f"Message: {a.get('message', '')}"
            )

        for d in discussions:
            text_chunks.append(
                f"Discussion: {d.get('title')} | {d.get('message', '')}"
            )

        if not text_chunks:
            raise HTTPException(status_code=400, detail="No data found for this course.")

        # 🧠 Create embeddings
        embeddings = []
        batch_size = 50

        for i in range(0, len(text_chunks), batch_size):
            batch = text_chunks[i:i + batch_size]
            response = client.embeddings.create(
                model="text-embedding-3-large",
                input=batch
            )
            for j, emb in enumerate(response.data):
                embeddings.append({
                    "id": f"{course_id}-{i+j}",
                    "values": emb.embedding,
                    "metadata": {"text": batch[j]}
                })

        # 🪣 Upload to Pinecone
        namespace = f"course_{course_id}"
        index.upsert(vectors=embeddings, namespace=namespace)

        return {
            "status": "ok",
            "course": course_name,
            "chunks_indexed": len(embeddings)
        }

    except Exception as e:
        print("\n❌ ERROR TRACEBACK:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
