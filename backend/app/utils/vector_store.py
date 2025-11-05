import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "canvas-ai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

pc = Pinecone(api_key=PINECONE_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ Create Pinecone index if it doesn't exist
if PINECONE_INDEX not in [i["name"] for i in pc.list_indexes()]:
    pc.create_index(
        name=PINECONE_INDEX,
        dimension=3072,  # dimension for text-embedding-3-large
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

index = pc.Index(PINECONE_INDEX)


def embed_text(text: str) -> list[float]:
    """Generate and return an embedding vector for the given text."""
    resp = client.embeddings.create(
        model="text-embedding-3-large",
        input=text,
    )
    return resp.data[0].embedding


def upsert_chunks(course_id: int, chunks: list[dict]):
    """
    Upload multiple text chunks as vectors to Pinecone for a course.
    Each chunk = { "id": str, "text": str, "metadata": dict }
    """
    vectors = []
    for ch in chunks:
        emb = embed_text(ch["text"])
        vectors.append(
            {
                "id": ch["id"],
                "values": emb,
                "metadata": {
                    "course_id": str(course_id),
                    "text": ch["text"],
                    **ch.get("metadata", {}),
                },
            }
        )
    index.upsert(vectors=vectors, namespace=f"course_{course_id}")


def query_course(course_id: int, query: str, top_k: int = 5):
    """Query Pinecone namespace for a course using semantic similarity search."""
    q_emb = embed_text(query)
    res = index.query(
        vector=q_emb,
        top_k=top_k,
        include_metadata=True,
        namespace=f"course_{course_id}",
    )
    return res.matches
