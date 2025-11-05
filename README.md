# 🎓 ClassGPT

**ClassGPT** is a full-stack **AI-powered academic assistant** that transforms how students and instructors interact with **Canvas LMS**.  
It syncs real course content — assignments, announcements, and discussions — and lets users ask **natural-language questions** like:

> “What’s due tomorrow?”  
> “When is my project presentation?”  
> “Show me all announcements from this week.”

ClassGPT retrieves verified Canvas data and answers with context-aware, intelligent responses — all inside a sleek chat interface.

---

## ⚙️ How It Works

1. **Course Data Ingestion**  
   ClassGPT connects securely to the Canvas LMS API to fetch assignments, announcements, discussions, and instructor information for each enrolled course.

2. **Data Cleaning & Embedding**  
   The system preprocesses and chunks course text before converting it into semantic embeddings using **OpenAI’s text-embedding-3-large** model.

3. **Vector Storage**  
   Each embedding is stored in **Pinecone**, a high-performance vector database, allowing ClassGPT to perform semantic searches across course data.

4. **Question Answering**  
   When a user asks a question, ClassGPT retrieves the most relevant content from Pinecone and uses **GPT-4o-mini** to generate an accurate, concise, and course-specific answer.

5. **Session Memory**  
   **Upstash Redis** powers temporary, per-session memory — enabling follow-up questions within the same chat.  
   Memory clears automatically upon refresh, ensuring privacy and lightweight operation.

6. **Interactive Chat UI**  
   The frontend, built with **React (Vite)**, offers a modern chat experience where each Canvas course opens its own AI-powered conversation.

---

## 🧩 Core Features

- 🎓 **Canvas-Integrated AI** – Directly understands your course materials.  
- 🗓️ **Smart Deadline Tracking** – Detects and summarizes due dates and grading details.  
- 💬 **Conversational Q&A** – Natural-language chat with contextual understanding.  
- ⚡ **Fast & Scalable** – Async backend and serverless Redis for performance.  
- 🧠 **Retrieval-Augmented Generation (RAG)** – Combines vector search with generative AI for factual accuracy.  
- 🔐 **Secure OAuth Integration** – Canvas login and token handling with FastAPI.  
- 🧰 **Clean User Interface** – Responsive chat with typing animations and auto-scroll.

---

## 🧱 Technology Stack

| Layer | Technology |
|-------|-------------|
| **Frontend** | React (Vite), Axios, modern CSS |
| **Backend** | FastAPI (Python 3.11), Async HTTPX, Pydantic |
| **AI Models** | OpenAI GPT-4o-mini, text-embedding-3-large |
| **Vector Database** | Pinecone |
| **Session Memory** | Upstash Redis |
| **Integration** | Canvas LMS REST API (v1) |
| **Environment Management** | Python dotenv |
| **Deployment Targets** | Render, Railway, Vercel, or Netlify |

---

## 🧭 System Architecture

