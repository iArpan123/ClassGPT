from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, traceback
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
        # Step 1 – Embed the user’s query
        emb = client.embeddings.create(
            model="text-embedding-3-large",
            input=req.message
        ).data[0].embedding

        # Step 2 – Search Pinecone for most similar chunks
        namespace = f"course_{req.course_id}"
        search = index.query(
            vector=emb,
            top_k=5,
            include_metadata=True,
            namespace=namespace
        )

        context = "\n\n".join([
            m["metadata"]["text"] for m in search.get("matches", [])
        ]) or "No relevant course data found."

        # Step 3 – Feed context + question into GPT
        system_prompt = f"""
        You are a professional Canvas course assistant.
        Use only the following course context to answer clearly and accurately.

        Course context:
        {context}

        If the user asks about grades or private info, politely say
        you don't have access to that.  Keep responses concise and factual.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message},
            ],
            max_tokens=400,
        )

        answer = response.choices[0].message.content.strip()
        return {"answer": answer}

    except Exception as e:
        print("\n❌ BACKEND ERROR:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
