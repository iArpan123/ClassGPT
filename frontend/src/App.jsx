import React, { useState } from "react";
import CourseList from "./components/CourseList";
import ChatWindow from "./components/ChatWindow";

export default function App() {
  const [selectedCourse, setSelectedCourse] = useState(null);

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#f5f6f8",
        color: "#1d1d1d",
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      {!selectedCourse ? (
        <CourseList onSelectCourse={setSelectedCourse} />
      ) : (
        <ChatWindow
          course={selectedCourse}
          onBack={() => setSelectedCourse(null)}
        />
      )}
    </div>
  );
}
