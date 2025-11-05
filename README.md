# 🧠 Canvas AI Buddy

Canvas AI Buddy is a full-stack **AI-powered assistant** built to make interacting with your **Canvas LMS** smarter and faster.  
It syncs real course content like assignments, announcements, and discussions — then lets you ask **natural-language questions** such as:

> “What’s due tomorrow?”  
> “When is my project presentation?”  
> “List all announcements posted this week.”

The system retrieves real data from Canvas and answers with precise, context-aware responses using advanced AI.

---

## ⚙️ How It Works

1. **Course Data Ingestion**  
   The backend connects to the Canvas LMS API to fetch assignments, announcements, discussions, and instructor data for each course.

2. **Data Processing & Embedding**  
   The text is cleaned and chunked using NLP preprocessing, then embedded via **OpenAI’s text-embedding-3-large** model to create high-dimensional semantic vectors.

3. **Vector Storage**  
   All embeddings are stored in **Pinecone**, a high-speed vector database optimized for similarity search.

4. **Retrieval & Answer Generation**  
   When a user asks a question, Pinecone retrieves the most relevant course content.  
   The context is then sent to **GPT-4o-mini**, which crafts a clear, accurate, and course-specific response.

5. **Session Memory**  
   **Upstash Redis** keeps short-term memory for each chat session — allowing follow-up questions without reloading context.  
   The memory resets automatically when the page refreshes for privacy.

6. **Frontend Chat Interface**  
   A minimal, intuitive **React (Vite)** interface allows users to select a course, chat, and get real-time AI answers in a clean conversational layout.

---

## 🧩 Core Features

- 🎓 **Canvas-Integrated Intelligence** – Learns directly from your course data.  
- 🗓️ **Smart Assignment Tracking** – Understands due dates, deadlines, and grading details.  
- 💬 **Conversational Q&A** – Natural-language queries with short-term memory.  
- ⚡ **Fast & Secure** – Async processing with serverless Redis memory.  
- 🧠 **RAG Architecture** – Combines retrieval-augmented generation for reliable answers.  
- 🌐 **OAuth Login** – Secure Canvas authentication with token exchange.  
- 🧰 **Modern Frontend UX** – Smooth chat experience, responsive design, and clear visuals.

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
## 🧭 System Architecture

