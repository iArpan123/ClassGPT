import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000", // your FastAPI backend
});

export const getCourses = async () => {
  const res = await API.get("/courses");
  return res.data;
};

export const sendChat = async (courseId, message) => {
  const res = await API.post("/chat", { course_id: courseId, message });
  return res.data;
};
