from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, traceback, re
from datetime import datetime, timezone
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)


class ChatRequest(BaseModel):
    course_id: int
    message: str


@router.post("/chat")
async def chat_with_canvas(req: ChatRequest):
    try:
        # 1️⃣ Embed the user query
        emb = client.embeddings.create(
            model="text-embedding-3-large",
            input=req.message
        ).data[0].embedding

        # 2️⃣ Search Pinecone for top results
        namespace = f"course_{req.course_id}"
        search = index.query(
            vector=emb,
            top_k=10,
            include_metadata=True,
            namespace=namespace
        )

        matches = [m["metadata"]["text"] for m in search.get("matches", [])]
        if not matches:
            return {"answer": "I couldn’t find relevant data for this course."}

        # 3️⃣ Filter and sort assignments by due date (from context)
        assignments = []
        for text in matches:
            if "Assignment:" in text or "Homework" in text:
                match = re.search(r"Due:\s*([A-Za-z]+\s\d{1,2},\s\d{4})", text)
                if match:
                    try:
                        date_str = match.group(1)
                        due_dt = datetime.strptime(date_str, "%B %d, %Y")
                        if due_dt >= datetime.now():
                            assignments.append((due_dt, text))
                    except Exception:
                        continue

        assignments.sort(key=lambda x: x[0])
        upcoming_context = "\n\n".join([a[1] for a in assignments[:3]]) if assignments else ""

        # 4️⃣ Combine all retrieved context if nothing upcoming
        context = upcoming_context or "\n\n".join(matches)
        if not context:
            context = "No relevant course data found."

        # 5️⃣ Date awareness and smart reasoning
        today = datetime.now(timezone.utc).strftime("%B %d, %Y")

        system_prompt = f"""
        You are an advanced Canvas academic assistant.
        Today's date is {today} (Arizona Time - MST).
        Use the provided course context to answer clearly, accurately, and professionally.

        Behavior rules:
        - If the user asks about the next assignment, find the *nearest future due date*.
        - If user mentions a specific assignment (like "Homework 2"), locate and describe that assignment.
        - Always display due dates in Arizona local time (MST) if available.
        - Never mix past assignments in your response unless explicitly asked.
        - If the question is about TAs, professors, or contact info, use context.
        - If about grades, say you don’t have access.
        - Keep responses short, factual, and well formatted.

        Course context (filtered and time-aware):
        {context}
        """

        # 6️⃣ Generate AI response
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message},
            ],
            max_tokens=500,
        )

        answer = response.choices[0].message.content.strip()
        return {"answer": answer}

    except Exception as e:
        print("\n❌ BACKEND ERROR:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
