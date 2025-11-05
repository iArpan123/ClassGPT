import React, { useState, useEffect, useRef } from "react";
import { sendChat } from "../api/api";

export default function ChatWindow({ course, onBack }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      const res = await sendChat(course.id, input);
      const botMsg = { role: "assistant", content: res.answer || "..." };
      setMessages((prev) => [...prev, botMsg]);
    } catch {
      const errorMsg = {
        role: "assistant",
        content: "⚠️ Sorry, something went wrong while fetching the answer.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  // Send message on Enter (Shift+Enter adds newline)
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "#f9fafb",
      }}
    >
      {/* Header */}
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

      {/* Chat messages */}
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
              justifyContent: m.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                backgroundColor: m.role === "user" ? "#3949ab" : "#e9ecf5",
                color: m.role === "user" ? "#fff" : "#1d1d1d",
                padding: "10px 14px",
                borderRadius: "16px",
                maxWidth: "65%",
                fontSize: "0.95rem",
                lineHeight: "1.4",
                whiteSpace: "pre-wrap",
              }}
            >
              {m.content}
            </div>
          </div>
        ))}

        {isTyping && (
          <div
            style={{
              display: "flex",
              justifyContent: "flex-start",
              marginBottom: "1rem",
            }}
          >
            <div
              style={{
                background: "#e9ecf5",
                color: "#1d1d1d",
                padding: "10px 14px",
                borderRadius: "16px",
                fontSize: "0.95rem",
              }}
            >
              <TypingDots />
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input bar */}
      <div
        style={{
          display: "flex",
          padding: "1rem",
          backgroundColor: "#f5f6f8",
          borderTop: "1px solid #ccc",
        }}
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about assignments, grading policy, etc..."
          style={{
            flex: 1,
            padding: "12px",
            borderRadius: "8px",
            border: "1px solid #ccc",
            outline: "none",
            fontSize: "1rem",
            resize: "none",
            height: "50px",
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

function TypingDots() {
  const [dots, setDots] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length === 3 ? "" : prev + "."));
    }, 400);
    return () => clearInterval(interval);
  }, []);

  return <span>AI is answering{dots}</span>;
}
