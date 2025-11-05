from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, traceback, re, json
from datetime import datetime, timezone
from openai import OpenAI
from pinecone import Pinecone
from upstash_redis import Redis
from dotenv import load_dotenv

load_dotenv()

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
    # Memory expires after 30 minutes (temporary session)
    redis_client.set(key, json.dumps(history), ex=1800)


def parse_date_from_text(text: str):
    """
    Extract and parse dates from multiple formats found in Canvas data
    """
    # Pattern 1: ISO 8601 format (2025-12-06T06:59:59Z)
    iso_pattern = r"Due:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"
    match = re.search(iso_pattern, text)
    if match:
        try:
            date_str = match.group(1)
            # Parse ISO format and convert to naive datetime
            due_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
            return due_date
        except Exception as e:
            print(f"⚠️ Failed to parse ISO date '{match.group(1)}': {e}")
    
    # Pattern 2: Readable format variations
    readable_patterns = [
        r"[Dd]ue[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",  # Due: Month DD, YYYY
        r"[Dd]ue\s+[Dd]ate[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"[Dd]eadline[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"[Ss]ubmit\s+by[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
    ]
    
    for pattern in readable_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                date_str = match.group(1).replace(",", "").strip()
                # Try full month name first
                try:
                    return datetime.strptime(date_str, "%B %d %Y")
                except:
                    # Try abbreviated month name
                    return datetime.strptime(date_str, "%b %d %Y")
            except Exception as e:
                print(f"⚠️ Failed to parse readable date '{match.group(1)}': {e}")
                continue
    
    return None


@router.post("/chat")
async def chat_with_canvas(req: ChatRequest):
    try:
        print(f"\n{'='*60}")
        print(f"📩 NEW QUERY: {req.message}")
        print(f"📚 Course ID: {req.course_id} | Session: {req.session_id}")
        
        # 🧠 Load session memory (per course & session)
        history = get_chat_history(req.course_id, req.session_id)
        recent_messages = [{"role": h["role"], "content": h["content"]} for h in history[-5:]]

        # 1️⃣ Embed the user query
        emb = client.embeddings.create(
            model="text-embedding-3-large",
            input=req.message
        ).data[0].embedding

        # 2️⃣ Search Pinecone for top results
        namespace = f"course_{req.course_id}"
        search = index.query(
            vector=emb,
            top_k=20,  # Increased even more for better coverage
            include_metadata=True,
            namespace=namespace
        )

        matches = search.get("matches", [])
        print(f"📊 Retrieved {len(matches)} documents from Pinecone")
        
        if not matches:
            print("⚠️ No matches found in Pinecone")
            return {"answer": "I couldn't find relevant data for this course."}

        # 3️⃣ Enhanced assignment detection and parsing
        assignments = []
        announcements = []
        other_context = []
        
        today = datetime.now()
        print(f"📅 Today's date: {today.strftime('%B %d, %Y')}")
        
        for i, m in enumerate(matches):
            text = m["metadata"]["text"]
            score = m.get("score", 0)
            
            print(f"\n--- Document {i+1} (score: {score:.4f}) ---")
            print(f"{text[:200]}..." if len(text) > 200 else text)
            
            # Parse due date
            due_date = parse_date_from_text(text)
            if due_date:
                print(f"✅ Found due date: {due_date.strftime('%B %d, %Y')}")
            
            # Classify document type
            is_assignment = text.startswith("Assignment:")
            is_announcement = text.startswith("Announcement:")
            
            # More comprehensive keyword detection
            assignment_keywords = [
                'assignment', 'homework', 'project', 'due', 'submit', 
                'deliverable', 'module', 'quiz', 'exam', 'deadline',
                'task', 'work', 'complete', 'turn in', 'retrospective',
                'report', 'presentation', 'poster'
            ]
            
            has_assignment_keywords = any(keyword in text.lower() for keyword in assignment_keywords)
            
            # Categorize
            if is_assignment and due_date and due_date >= today:
                assignments.append({
                    'date': due_date,
                    'text': text,
                    'score': score
                })
                print(f"📝 Categorized as: UPCOMING ASSIGNMENT")
            elif is_announcement:
                announcements.append({
                    'text': text,
                    'score': score,
                    'date': due_date  # might be None
                })
                print(f"📢 Categorized as: ANNOUNCEMENT")
            else:
                other_context.append({
                    'text': text,
                    'score': score
                })
                reason = "past due" if (due_date and due_date < today) else "no due date"
                print(f"📄 Categorized as: OTHER CONTEXT ({reason})")

        # Sort assignments by date (earliest first)
        assignments.sort(key=lambda x: x['date'])
        
        print(f"\n{'='*60}")
        print(f"✅ Found {len(assignments)} upcoming assignments")
        print(f"📢 Found {len(announcements)} announcements")
        print(f"📄 Found {len(other_context)} other relevant documents")
        
        if assignments:
            print("\n📋 UPCOMING ASSIGNMENTS:")
            for i, assignment in enumerate(assignments, 1):
                date_str = assignment['date'].strftime("%B %d, %Y")
                preview = assignment['text'][:150].replace('\n', ' ')
                print(f"  [{i}] {date_str}: {preview}...")
        
        # 4️⃣ Build intelligent context
        context_parts = []
        
        # Add upcoming assignments section (show ALL of them, not just top 5)
        if assignments:
            context_parts.append("=== UPCOMING ASSIGNMENTS (sorted by due date, earliest first) ===")
            for i, assignment in enumerate(assignments, 1):
                date_str = assignment['date'].strftime("%B %d, %Y")
                context_parts.append(f"\n[Assignment {i}] Due: {date_str}\n{assignment['text']}")
        
        # Add relevant announcements
        if announcements:
            context_parts.append("\n\n=== RECENT ANNOUNCEMENTS ===")
            # Sort by relevance score
            announcements.sort(key=lambda x: x['score'], reverse=True)
            for ann in announcements[:5]:  # Top 5 most relevant announcements
                context_parts.append(ann['text'])
        
        # Add other relevant context
        if other_context:
            context_parts.append("\n\n=== ADDITIONAL COURSE INFORMATION ===")
            # Sort by relevance score and take top 3
            other_context.sort(key=lambda x: x['score'], reverse=True)
            for ctx in other_context[:3]:
                context_parts.append(ctx['text'])
        
        context = "\n\n".join(context_parts)
        
        if not context.strip():
            context = "No relevant course data found."

        # 5️⃣ Enhanced system prompt
        today_str = today.strftime("%B %d, %Y")
        system_prompt = f"""You are an advanced Canvas academic assistant with access to course materials, announcements, and assignments.

TODAY'S DATE: {today_str} (Arizona Time - MST/Mountain Time)

CRITICAL INSTRUCTIONS:
- Answer ONLY based on the provided course context - never make up information
- For follow-up questions, use conversation memory (e.g., "their email" refers to the last mentioned instructor)
- When asked about assignments or due dates:
  * Check the UPCOMING ASSIGNMENTS section CAREFULLY
  * List ALL relevant assignments in chronological order (earliest first)
  * Include the exact due dates from the context
  * If asked for "next" assignment, give the soonest one
  * If asked for "upcoming" assignments, list multiple assignments
- Check the RECENT ANNOUNCEMENTS section for schedule information, presentation dates, and other time-sensitive info
- If information about schedules, presentations, or specific sections is in announcements, use that information
- Be specific about dates, times, and requirements from the context
- If information is not in the provided context, clearly say "I don't have that information in the course materials"
- Keep responses concise but complete
- You don't have access to grades or submission status

COURSE CONTEXT:
{context}
"""

        # 6️⃣ Generate AI response with memory
        messages = [{"role": "system", "content": system_prompt}] + recent_messages + [
            {"role": "user", "content": req.message}
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=700,  # Increased for more complete responses
            temperature=0.2,  # Even lower for more factual responses
        )

        answer = response.choices[0].message.content.strip()
        print(f"\n🤖 AI Response: {answer}")
        print(f"{'='*60}\n")

        # 7️⃣ Save updated conversation
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": answer})
        save_chat_history(req.course_id, req.session_id, history)

        return {"answer": answer}

    except Exception as e:
        print("\n❌ BACKEND ERROR:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/reset")
async def reset_memory(course_id: int, session_id: str):
    """Reset conversation memory for a specific course and session"""
    key = get_memory_key(course_id, session_id)
    redis_client.delete(key)
    print(f"🗑️ Memory cleared for course {course_id}, session {session_id}")
    return {"status": "memory cleared"}


@router.get("/debug/pinecone/{course_id}")
async def debug_pinecone_data(course_id: int, search_term: str = None):
    """Debug endpoint to see what's stored in Pinecone for a course"""
    try:
        namespace = f"course_{course_id}"
        
        # Get index stats - convert to dict explicitly
        stats = index.describe_index_stats()
        stats_dict = {
            "dimension": stats.dimension,
            "index_fullness": stats.index_fullness,
            "total_vector_count": stats.total_vector_count,
            "namespaces": {ns: {"vector_count": info.vector_count} for ns, info in stats.namespaces.items()}
        }
        
        if search_term:
            # Search for specific term
            emb = client.embeddings.create(
                model="text-embedding-3-large",
                input=search_term
            ).data[0].embedding
            
            sample_query = index.query(
                vector=emb,
                top_k=10,
                include_metadata=True,
                namespace=namespace
            )
        else:
            # Random sample
            sample_query = index.query(
                vector=[0.0] * 3072,
                top_k=10,
                include_metadata=True,
                namespace=namespace
            )
        
        documents = []
        for match in sample_query.get("matches", []):
            text = match["metadata"]["text"]
            due_date = parse_date_from_text(text)
            
            documents.append({
                "id": match.get("id"),
                "score": float(match.get("score", 0)),
                "type": "Assignment" if text.startswith("Assignment:") else "Announcement" if text.startswith("Announcement:") else "Other",
                "due_date": due_date.strftime("%B %d, %Y") if due_date else None,
                "text_length": len(text),
                "text_preview": text[:300] + "..." if len(text) > 300 else text,
                "full_text": text
            })
        
        return {
            "namespace": namespace,
            "search_term": search_term or "random_sample",
            "index_stats": stats_dict,
            "sample_documents": documents,
            "total_vectors_in_namespace": stats_dict["namespaces"].get(namespace, {}).get("vector_count", 0)
        }
    
    except Exception as e:
        print("\n❌ DEBUG ERROR:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))