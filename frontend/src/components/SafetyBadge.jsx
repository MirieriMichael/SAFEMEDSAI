import React from "react";

const badgeStyles = {
  "Health Risk": "badge-danger",
  "Use With Caution": "badge-warning",
  "Mild Caution": "badge-info",
  "Safe": "badge-success",
};

export default function SafetyBadge({ safety }) {
  if (!safety) return null;

  const badge = badgeStyles[safety.safety_badge] || "badge-default";
  const expl = safety.explanation || "Additional caution may be needed.";

  return (
    <div style={{ 
      display: "flex", 
      gap: "10px", 
      alignItems: "center",
      marginTop: "10px",
      padding: "10px",
      borderRadius: "6px",
      background: safety.safety_badge === "Health Risk" ? "rgba(239, 68, 68, 0.1)" :
                   safety.safety_badge === "Use With Caution" ? "rgba(245, 158, 11, 0.1)" :
                   safety.safety_badge === "Mild Caution" ? "rgba(59, 130, 246, 0.1)" :
                   "rgba(34, 197, 94, 0.1)",
      border: `1px solid ${
        safety.safety_badge === "Health Risk" ? "#ef4444" :
        safety.safety_badge === "Use With Caution" ? "#f59e0b" :
        safety.safety_badge === "Mild Caution" ? "#3b82f6" :
        "#22c55e"
      }`
    }}>
      <span 
        className={`badge ${badge}`}
        style={{
          padding: "4px 12px",
          borderRadius: "4px",
          fontWeight: "600",
          fontSize: "0.85rem",
          color: "#fff",
          background: safety.safety_badge === "Health Risk" ? "#ef4444" :
                      safety.safety_badge === "Use With Caution" ? "#f59e0b" :
                      safety.safety_badge === "Mild Caution" ? "#3b82f6" :
                      "#22c55e"
        }}
      >
        {safety.safety_badge}
      </span>
      <small style={{ 
        opacity: 0.9, 
        color: "#e5e7eb",
        fontSize: "0.9rem",
        lineHeight: "1.4"
      }}>
        {expl}
      </small>
    </div>
  );
}

