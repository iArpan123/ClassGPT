import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000", // your FastAPI backend
});

// 🧠 Temporary session ID (resets on page refresh)
const sessionId = crypto.randomUUID(); 
// Each time the page reloads, a new session starts — old memory is gone

// 🔹 Send chat message to backend
export const sendChat = async (courseId, message) => {
  const res = await API.post("/chat", {
    course_id: courseId,
    session_id: sessionId, // include session ID for temporary memory
    message,
  });
  return res.data;
};

// 🔹 Get all courses (unchanged)
export const getCourses = async () => {
  const res = await API.get("/courses");
  return res.data;
};

// 🧹 Optional: reset memory manually (if you add a “Clear Chat” button later)
export const resetChatMemory = async (courseId) => {
  const res = await API.delete(`/chat/reset`, {
    data: { course_id: courseId, session_id: sessionId },
  });
  return res.data;
};
