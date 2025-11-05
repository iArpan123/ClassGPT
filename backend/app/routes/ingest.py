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

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@router.post("/ingest/{course_id}")
async def ingest_course(course_id: int):
    try:
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

        async with httpx.AsyncClient() as http:
            # 1️⃣ Fetch course and syllabus
            course_res = await http.get(
                f"{BASE_URL}/api/v1/courses/{course_id}",
                headers=headers,
                params={"include[]": "syllabus_body"},
            )
            course = course_res.json()
            course_name = course.get("name", "Unknown Course")
            syllabus = course.get("syllabus_body", "")

            # 2️⃣ Fetch assignments
            assignments_res = await http.get(
                f"{BASE_URL}/api/v1/courses/{course_id}/assignments",
                headers=headers,
                params={"per_page": 100},
            )
            assignments = assignments_res.json()

            # 3️⃣ Fetch announcements
            announcements_res = await http.get(
                f"{BASE_URL}/api/v1/announcements",
                headers=headers,
                params={"context_codes[]": f"course_{course_id}", "per_page": 50},
            )
            announcements = announcements_res.json()

            # 4️⃣ Fetch discussions
            discussions_res = await http.get(
                f"{BASE_URL}/api/v1/courses/{course_id}/discussion_topics",
                headers=headers,
                params={"per_page": 50},
            )
            discussions = discussions_res.json()

            # 5️⃣ Fetch instructors and TAs
            people_res = await http.get(
                f"{BASE_URL}/api/v1/courses/{course_id}/users",
                headers=headers,
                params={"enrollment_type[]": ["teacher", "ta"], "per_page": 50},
            )
            people = people_res.json()

        # 🧠 Create text chunks
        text_chunks = []

        if syllabus:
            text_chunks.append(f"Syllabus for {course_name}: {syllabus}")

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
                f"Discussion: {d.get('title')} | Message: {d.get('message', '')}"
            )

        for p in people:
            name = p.get("name", "Unknown")
            role = p.get("enrollments", [{}])[0].get("type", "Staff")
            email = f"{p.get('login_id', '')}@asu.edu"
            text_chunks.append(f"{role}: {name} | Email: {email}")

        if not text_chunks:
            raise HTTPException(status_code=400, detail="No course data found.")

        # 🧩 Generate embeddings in batches
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
