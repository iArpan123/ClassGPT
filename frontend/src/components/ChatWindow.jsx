import React, { useState } from "react";
import { sendChat } from "../api/api";

export default function ChatWindow({ course, onBack }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { role: "user", content: input };
    setMessages([...messages, userMsg]);
    setInput("");

    try {
      const res = await sendChat(course.id, input);
      const botMsg = { role: "assistant", content: res.answer || "..." };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "#f5f6f8",
      }}
    >
      {/* Top Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          backgroundColor: "#3949ab",
          color: "#fff",
          padding: "0.8rem 1.2rem",
        }}
      >
        <button
          onClick={onBack}
          style={{
            background: "transparent",
            border: "none",
            color: "#fff",
            fontSize: "1.2rem",
            marginRight: "1rem",
            cursor: "pointer",
          }}
        >
          ←
        </button>
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>{course.name}</h2>
      </div>

      {/* Chat Area */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "1rem 2rem",
          backgroundColor: "#fff",
        }}
      >
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              marginBottom: "1rem",
              display: "flex",
              justifyContent:
                m.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                backgroundColor:
                  m.role === "user" ? "#3949ab" : "#e0e0e0",
                color: m.role === "user" ? "#fff" : "#000",
                padding: "10px 14px",
                borderRadius: "16px",
                maxWidth: "60%",
              }}
            >
              {m.content}
            </div>
          </div>
        ))}
      </div>

      {/* Input Area */}
      <div
        style={{
          display: "flex",
          padding: "1rem",
          backgroundColor: "#f5f6f8",
          borderTop: "1px solid #ccc",
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about assignments, grading policy, etc..."
          style={{
            flex: 1,
            padding: "12px",
            borderRadius: "8px",
            border: "1px solid #ccc",
            outline: "none",
            fontSize: "1rem",
          }}
        />
        <button
          onClick={handleSend}
          style={{
            marginLeft: "10px",
            padding: "12px 20px",
            backgroundColor: "#3949ab",
            color: "#fff",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
