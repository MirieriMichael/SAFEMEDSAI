// frontend/src/CollapsibleCard.jsx
import React, { useState } from 'react';

function CollapsibleCard({ title, content }) {
  const [isOpen, setIsOpen] = useState(false);

  // If there's no content to display, show a simple placeholder and don't make it a button.
  if (!content || content === 'No information available.') {
    return (
        <div className="collapsible-card-static">
            <strong>{title}:</strong> N/A
        </div>
    );
  }

  return (
    <div className="collapsible-card">
      <button className="collapsible-header" onClick={() => setIsOpen(!isOpen)}>
        <span>{title}</span>
        <span className="collapsible-icon">{isOpen ? '−' : '+'}</span>
      </button>
      {isOpen && (
        <div className="collapsible-content">
          {/* This handles content that might have multiple lines */}
          {content.split('\n').map((paragraph, index) => (
            paragraph.trim() && <p key={index}>{paragraph.trim()}</p>
          ))}
        </div>
      )}
    </div>
  );
}

export default CollapsibleCard;