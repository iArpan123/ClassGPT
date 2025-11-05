import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000", // Replace with production backend URL in deployment
});

// Generate a unique session ID per browser session
const sessionId = crypto.randomUUID();

/**
 * Send a chat message to the FastAPI backend
 * @param {number} courseId
 * @param {string} message
 */
export const sendChat = async (courseId, message) => {
  const res = await API.post("/chat", {
    course_id: courseId,
    session_id: sessionId,
    message,
  });
  return res.data;
};

/**
 * Fetch the user's available courses
 */
export const getCourses = async () => {
  const res = await API.get("/courses");
  return res.data;
};

/**
 * Reset the chat memory for the current session
 * (useful if you add a “Clear Chat” button)
 */
export const resetChatMemory = async (courseId) => {
  const res = await API.delete("/chat/reset", {
    data: { course_id: courseId, session_id: sessionId },
  });
  return res.data;
};
