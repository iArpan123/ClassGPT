from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, traceback, re, json
from datetime import datetime
from openai import OpenAI
from pinecone import Pinecone
from upstash_redis import Redis
from dotenv import load_dotenv

load_dotenv()  # Load environment variables safely

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Pinecone setup ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

# --- Upstash Redis setup ---
redis_client = Redis.from_env()

# --- Request model ---
class ChatRequest(BaseModel):
    course_id: int
    session_id: str  # unique for this browser session
    message: str


# --- Redis helper functions ---
def get_memory_key(course_id: int, session_id: str):
    return f"chat:{course_id}:{session_id}"


def get_chat_history(course_id: int, session_id: str):
    key = get_memory_key(course_id, session_id)
    history_json = redis_client.get(key)
    if history_json:
        return json.loads(history_json)
    return []


def save_chat_history(course_id: int, session_id: str, history):
    key = get_memory_key(course_id, session_id)
    redis_client.set(key, json.dumps(history), ex=1800)  # Expires after 30 minutes


def parse_date_from_text(text: str):
    """Extract and parse possible due dates from course text"""
    iso_pattern = r"Due:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"
    match = re.search(iso_pattern, text)
    if match:
        try:
            date_str = match.group(1)
            due_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
            return due_date
        except Exception:
            pass

    readable_patterns = [
        r"[Dd]ue[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"[Dd]ue\s+[Dd]ate[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"[Dd]eadline[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"[Ss]ubmit\s+by[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
    ]

    for pattern in readable_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                date_str = match.group(1).replace(",", "").strip()
                try:
                    return datetime.strptime(date_str, "%B %d %Y")
                except:
                    return datetime.strptime(date_str, "%b %d %Y")
            except Exception:
                continue
    return None


@router.post("/chat")
async def chat_with_canvas(req: ChatRequest):
    """Main chat endpoint: retrieves context, queries Pinecone, and responds via OpenAI"""
    try:
        history = get_chat_history(req.course_id, req.session_id)
        recent_messages = [{"role": h["role"], "content": h["content"]} for h in history[-5:]]

        emb = client.embeddings.create(
            model="text-embedding-3-large",
            input=req.message
        ).data[0].embedding

        namespace = f"course_{req.course_id}"
        search = index.query(
            vector=emb,
            top_k=20,
            include_metadata=True,
            namespace=namespace
        )

        matches = search.get("matches", [])
        if not matches:
            return {"answer": "I couldn't find relevant data for this course."}

        assignments, announcements, other_context = [], [], []
        today = datetime.now()

        for m in matches:
            text = m["metadata"]["text"]
            score = m.get("score", 0)
            due_date = parse_date_from_text(text)

            is_assignment = text.startswith("Assignment:")
            is_announcement = text.startswith("Announcement:")

            if is_assignment and due_date and due_date >= today:
                assignments.append({'date': due_date, 'text': text, 'score': score})
            elif is_announcement:
                announcements.append({'text': text, 'score': score, 'date': due_date})
            else:
                other_context.append({'text': text, 'score': score})

        assignments.sort(key=lambda x: x['date'])

        context_parts = []
        if assignments:
            context_parts.append("=== UPCOMING ASSIGNMENTS ===")
            for i, a in enumerate(assignments, 1):
                date_str = a['date'].strftime("%B %d, %Y")
                context_parts.append(f"[Assignment {i}] Due: {date_str}\n{a['text']}")
        if announcements:
            announcements.sort(key=lambda x: x['score'], reverse=True)
            context_parts.append("\n\n=== RECENT ANNOUNCEMENTS ===")
            for ann in announcements[:5]:
                context_parts.append(ann['text'])
        if other_context:
            other_context.sort(key=lambda x: x['score'], reverse=True)
            context_parts.append("\n\n=== ADDITIONAL COURSE INFORMATION ===")
            for ctx in other_context[:3]:
                context_parts.append(ctx['text'])
        context = "\n\n".join(context_parts) or "No relevant course data found."

        today_str = today.strftime("%B %d, %Y")
        system_prompt = f"""You are an advanced Canvas academic assistant with access to course materials.
TODAY'S DATE: {today_str}
Answer only using the provided context and course data.
COURSE CONTEXT:
{context}
"""

        messages = [{"role": "system", "content": system_prompt}] + recent_messages + [
            {"role": "user", "content": req.message}
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=700,
            temperature=0.2,
        )

        answer = response.choices[0].message.content.strip()

        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": answer})
        save_chat_history(req.course_id, req.session_id, history)

        return {"answer": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/reset")
async def reset_memory(course_id: int, session_id: str):
    """Reset conversation memory for a specific course and session"""
    key = get_memory_key(course_id, session_id)
    redis_client.delete(key)
    return {"status": "memory cleared"}
