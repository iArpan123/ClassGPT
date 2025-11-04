import React, { useEffect, useState } from "react";
import { getCourses } from "../api/api";

export default function CourseList({ onSelectCourse }) {
  const [courses, setCourses] = useState([]);

  useEffect(() => {
    getCourses()
      .then(setCourses)
      .catch((err) => console.error("Error loading courses:", err));
  }, []);

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "2rem" }}>
      <h1
        style={{
          fontWeight: 700,
          fontSize: "1.8rem",
          color: "#1d1d1d",
          marginBottom: "1.5rem",
        }}
      >
        Dashboard
      </h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
          gap: "1.5rem",
        }}
      >
        {courses.map((course) => {
          const color =
            course?.default_view === "wiki"
              ? "#009688"
              : course?.workflow_state === "available"
              ? "#1976d2"
              : "#6a1b9a";

          return (
            <div
              key={course.id}
              onClick={() => onSelectCourse(course)}
              style={{
                backgroundColor: "#fff",
                borderRadius: "8px",
                boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
                cursor: "pointer",
                transition: "transform 0.15s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.02)")}
              onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1.0)")}
            >
              {/* Header Banner */}
              <div
                style={{
                  height: "80px",
                  backgroundColor: color,
                  borderTopLeftRadius: "8px",
                  borderTopRightRadius: "8px",
                }}
              ></div>

              {/* Course Info */}
              <div style={{ padding: "1rem" }}>
                <h3
                  style={{
                    fontSize: "1rem",
                    fontWeight: 600,
                    color: "#1d1d1d",
                    marginBottom: "0.4rem",
                  }}
                >
                  {course.name}
                </h3>
                <p style={{ color: "#555", fontSize: "0.9rem", margin: 0 }}>
                  {course.course_code}
                </p>
                {course.term?.name && (
                  <p
                    style={{
                      color: "#777",
                      fontSize: "0.85rem",
                      marginTop: "0.4rem",
                    }}
                  >
                    {course.term.name}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
