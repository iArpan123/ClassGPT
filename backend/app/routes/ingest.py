from fastapi import APIRouter, HTTPException
import os, httpx, traceback, re
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

router = APIRouter()
BASE_URL = os.getenv("CANVAS_BASE_URL")
ACCESS_TOKEN = os.getenv("CANVAS_ACCESS_TOKEN")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def clean_html(html_text: str) -> str:
    """Remove HTML tags and extra whitespace"""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, max_chars: int = 2000, overlap: int = 200):
    """Split large text into overlapping chunks"""
    if not text:
        return [""]
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return [text]

    chunks, start = [], 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            last_period = text.rfind(".", start, end)
            if last_period > start + max_chars // 2:
                end = last_period + 1
        chunks.append(text[start:end])
        start = end - overlap if end < len(text) else len(text)
    return chunks


async def fetch_all_paginated(http, url, headers, params):
    """Fetch all pages of a paginated Canvas API endpoint"""
    all_items = []
    current_url = url
    while current_url:
        response = await http.get(current_url, headers=headers, params=params if current_url == url else None)
        items = response.json()
        if isinstance(items, list):
            all_items.extend(items)
        else:
            all_items.append(items)
            break
        link_header = response.headers.get("Link", "")
        next_link = None
        for link in link_header.split(","):
            if 'rel="next"' in link:
                next_link = link[link.find("<") + 1:link.find(">")]
                break
        current_url = next_link
        if len(all_items) > 500:
            break
    return all_items


@router.post("/ingest/{course_id}")
async def ingest_course(course_id: int):
    """Fetch Canvas data, embed it, and upload to Pinecone"""
    try:
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        async with httpx.AsyncClient(timeout=30.0) as http:
            course_res = await http.get(
                f"{BASE_URL}/api/v1/courses/{course_id}",
                headers=headers,
                params={"include[]": "syllabus_body"},
            )
            course = course_res.json()
            course_name = course.get("name", "Unknown Course")
            syllabus = course.get("syllabus_body", "")

            assignments = await fetch_all_paginated(
                http,
                f"{BASE_URL}/api/v1/courses/{course_id}/assignments",
                headers,
                {"per_page": 100}
            )
            announcements = await fetch_all_paginated(
                http,
                f"{BASE_URL}/api/v1/announcements",
                headers,
                {"context_codes[]": f"course_{course_id}", "per_page": 100}
            )
            discussions = await fetch_all_paginated(
                http,
                f"{BASE_URL}/api/v1/courses/{course_id}/discussion_topics",
                headers,
                {"per_page": 100}
            )
            people = await fetch_all_paginated(
                http,
                f"{BASE_URL}/api/v1/courses/{course_id}/users",
                headers,
                {"enrollment_type[]": ["teacher", "ta"], "per_page": 100}
            )

        embeddings, vector_id = [], 0

        # Syllabus
        if syllabus:
            clean_syllabus = clean_html(syllabus)
            chunks = chunk_text(clean_syllabus, max_chars=2000)
            for chunk in chunks:
                if chunk.strip():
                    embeddings.append({
                        "text": f"Syllabus for {course_name}: {chunk}",
                        "type": "syllabus",
                        "id": f"{course_id}-{vector_id}"
                    })
                    vector_id += 1

        # Assignments
        for a in assignments:
            name = a.get("name", "Untitled")
            due_at = a.get("due_at") or ""
            points = a.get("points_possible") or 0
            desc = clean_html(a.get("description", ""))
            chunks = chunk_text(desc, max_chars=2000) if desc else [""]
            for i, chunk in enumerate(chunks):
                text = f"Assignment: {name} | Due: {due_at} | Points: {points} | Description: {chunk}"
                metadata = {
                    "text": text,
                    "type": "assignment",
                    "name": name,
                    "chunk_index": i,
                    "id": f"{course_id}-{vector_id}"
                }
                if due_at:
                    metadata["due_date"] = due_at
                if points > 0:
                    metadata["points"] = float(points)
                embeddings.append(metadata)
                vector_id += 1

        # Announcements
        for ann in announcements:
            title = ann.get("title", "Untitled")
            posted_at = ann.get("posted_at") or ""
            message = clean_html(ann.get("message", ""))
            section_match = re.findall(r'\b\d{5}\b', title + " " + message)
            sections = list(set(section_match)) if section_match else []
            chunks = chunk_text(message, max_chars=2000) if message else [""]
            for i, chunk in enumerate(chunks):
                text = f"Announcement: {title} | Date: {posted_at} | {chunk}"
                metadata = {
                    "text": text,
                    "type": "announcement",
                    "title": title,
                    "chunk_index": i,
                    "id": f"{course_id}-{vector_id}"
                }
                if posted_at:
                    metadata["posted_date"] = posted_at
                if sections:
                    metadata["sections"] = ",".join(sections)
                embeddings.append(metadata)
                vector_id += 1

        # Discussions
        for d in discussions:
            title = d.get("title", "Untitled")
            message = clean_html(d.get("message", ""))
            chunks = chunk_text(message, max_chars=2000) if message else [""]
            for i, chunk in enumerate(chunks):
                text = f"Discussion: {title} | Content: {chunk}"
                embeddings.append({
                    "text": text,
                    "type": "discussion",
                    "title": title,
                    "chunk_index": i,
                    "id": f"{course_id}-{vector_id}"
                })
                vector_id += 1

        # People
        for p in people:
            name = p.get("name", "Unknown")
            enrollments = p.get("enrollments", [])
            role = enrollments[0].get("type", "Staff") if enrollments else "Staff"
            email = f"{p.get('login_id', 'unknown')}@asu.edu"
            text = f"{role}: {name} | Email: {email}"
            embeddings.append({
                "text": text,
                "type": "person",
                "name": name,
                "role": role,
                "email": email,
                "id": f"{course_id}-{vector_id}"
            })
            vector_id += 1

        if not embeddings:
            raise HTTPException(status_code=400, detail="No course data found.")

        # Create embeddings and upload to Pinecone
        vectors = []
        batch_size = 50
        for i in range(0, len(embeddings), batch_size):
            batch = embeddings[i:i + batch_size]
            texts = [item["text"] for item in batch]
            response = client.embeddings.create(
                model="text-embedding-3-large",
                input=texts
            )
            for j, emb_data in enumerate(response.data):
                item = batch[j]
                vectors.append({
                    "id": item["id"],
                    "values": emb_data.embedding,
                    "metadata": {k: v for k, v in item.items() if k != "id"}
                })

        namespace = f"course_{course_id}"
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch, namespace=namespace)

        return {
            "status": "success",
            "course": course_name,
            "stats": {
                "total_chunks": len(vectors),
                "assignments": len(assignments),
                "announcements": len(announcements),
                "discussions": len(discussions),
                "people": len(people)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ingest/{course_id}")
async def clear_course_data(course_id: int):
    """Delete all stored vectors for a specific course"""
    try:
        namespace = f"course_{course_id}"
        index.delete(delete_all=True, namespace=namespace)
        return {"status": "success", "message": f"Cleared namespace {namespace}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
