// // // frontend/src/CollapsibleCard.jsx
// // import React, { useState } from 'react';

// // function CollapsibleCard({ title, content }) {
// //   const [isOpen, setIsOpen] = useState(false);

// //   // If there's no content to display, show a simple placeholder and don't make it a button.
// //   if (!content || content === 'No information available.') {
// //     return (
// //         <div className="collapsible-card-static">
// //             <strong>{title}:</strong> N/A
// //         </div>
// //     );
// //   }

// //   return (
// //     <div className="collapsible-card">
// //       <button className="collapsible-header" onClick={() => setIsOpen(!isOpen)}>
// //         <span>{title}</span>
// //         <span className="collapsible-icon">{isOpen ? '−' : '+'}</span>
// //       </button>
// //       {isOpen && (
// //         <div className="collapsible-content">
// //           {/* This handles content that might have multiple lines */}
// //           {content.split('\n').map((paragraph, index) => (
// //             paragraph.trim() && <p key={index}>{paragraph.trim()}</p>
// //           ))}
// //         </div>
// //       )}
// //     </div>
// //   );
// // }

// // export default CollapsibleCard;
// import React, { useState } from 'react';

// function CollapsibleCard({ title, content }) {
//   const [isOpen, setIsOpen] = useState(false);

//   // Safe content conversion - handle string, object, or null
//   const safeContent = (c) => {
//     if (typeof c === 'string') return c.trim();
//     if (c == null) return '';
//     if (typeof c === 'object') return JSON.stringify(c, null, 2);
//     return String(c).trim();
//   };

//   const contentStr = safeContent(content);

//   // If there's no content to display, show a simple placeholder.
//   if (!contentStr || contentStr === 'No information available.' || contentStr === '') {
//     return (
//         <div className="collapsible-card-static" style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #374151', color: '#9ca3af', fontSize: '0.9rem' }}>
//             <strong>{title}:</strong> <span style={{marginLeft:'8px'}}>No detailed information available.</span>
//         </div>
//     );
//   }

//   // Render content - always render as string text (never unmount during transitions)
//   const renderedContent = (
//     <div className="collapsible-content-text">
//       {contentStr.split('\n').map((paragraph, index) => {
//         const trimmed = paragraph.trim();
//         return trimmed ? (
//           <p key={index} className="collapsible-paragraph">
//             {trimmed}
//           </p>
//         ) : null;
//       })}
//     </div>
//   );

//   return (
//     <div className="collapsible-card">
//       <button 
//         className={`collapsible-header ${isOpen ? 'open' : ''}`}
//         onClick={() => setIsOpen(!isOpen)}
//         aria-expanded={isOpen}
//       >
//         <span>{title}</span>
//         <span className="collapsible-icon">{isOpen ? '−' : '+'}</span>
//       </button>
      
//       {/* Always render content in DOM, only change CSS class for visibility */}
//       <div className={`collapsible-content ${isOpen ? 'open' : 'closed'}`}>
//         {renderedContent}
//       </div>
//     </div>
//   );
// }

// export default CollapsibleCard;
import React, { useState } from 'react';

function CollapsibleCard({ title, content, badge, onToggle, isOpen: controlledIsOpen }) {
  // Support both controlled and uncontrolled state
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const isOpen = controlledIsOpen !== undefined ? controlledIsOpen : internalIsOpen;
  
  const handleToggle = () => {
    if (controlledIsOpen === undefined) {
      setInternalIsOpen(!internalIsOpen);
    }
    if (onToggle) {
      onToggle(!isOpen);
    }
  };

  // Get badge color based on safety_badge value
  const getBadgeStyle = (badgeText) => {
    if (!badgeText) return {};
    
    const badgeLower = badgeText.toLowerCase().replace(/\s+/g, '-');
    const colors = {
      'health-risk': { background: '#b91c1c', color: '#fff' },
      'use-with-caution': { background: '#f59e0b', color: '#fff' },
      'caution': { background: '#f59e0b', color: '#fff' },
      'safe': { background: '#10b981', color: '#fff' },
    };
    
    return colors[badgeLower] || { background: '#6b7280', color: '#fff' };
  };

  // Extract badge from content if it's an object with safety_badge
  const displayBadge = badge || (content && typeof content === 'object' && content.safety_badge ? content.safety_badge : null);

  // Render ANY type of content safely
  const renderContent = (value) => {
    if (!value) return <p>No detailed information available.</p>;

    // If it's an array → render bullet points
    if (Array.isArray(value)) {
      if (value.length === 0) return <p>No relevant matches.</p>;
      return (
        <ul style={{ paddingLeft: "20px", margin: "8px 0" }}>
          {value.map((item, idx) => (
            <li key={idx} style={{ marginBottom: "4px", color: '#e5e7eb' }}>{String(item)}</li>
          ))}
        </ul>
      );
    }

    // If it's an object → render keys and values (skip safety_badge if it's used as badge)
    if (typeof value === "object") {
      const entries = Object.entries(value).filter(([key]) => 
        key !== 'safety_badge' || !displayBadge // Don't show safety_badge if it's displayed as badge
      );
      
      if (entries.length === 0) return <p>No information available.</p>;
      
      return (
        <div style={{ color: '#e5e7eb' }}>
          {entries.map(([key, val]) => (
            <div key={key} style={{ marginBottom: "12px" }}>
              <strong style={{ color: '#93c5fd', textTransform: 'capitalize' }}>
                {key.replace(/_/g, " ")}: 
              </strong>
              <div style={{ marginTop: "4px", marginLeft: "8px" }}>
                {Array.isArray(val) ? renderContent(val) : (typeof val === 'string' ? val.split('\n').map((line, i) => <p key={i} style={{ margin: '4px 0' }}>{line}</p>) : String(val))}
              </div>
            </div>
          ))}
        </div>
      );
    }

    // If it's a plain string → split into paragraphs
    if (typeof value === "string") {
      const lines = value.split("\n").filter(line => line.trim());
      if (lines.length === 0) return <p>No information available.</p>;
      return lines.map((line, idx) => (
        <p key={idx} style={{ margin: '8px 0', color: '#e5e7eb' }}>{line.trim()}</p>
      ));
    }

    return <p style={{ color: '#e5e7eb' }}>{String(value)}</p>;
  };

  // If there's no content to display
  if (!content || (typeof content === 'string' && content.trim() === '') || 
      (typeof content === 'object' && Object.keys(content).length === 0)) {
    return (
      <div className="collapsible-card-static" style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #374151', color: '#9ca3af', fontSize: '0.9rem' }}>
        <strong>{title}:</strong> <span style={{marginLeft:'8px'}}>No detailed information available.</span>
      </div>
    );
  }

  const badgeStyle = getBadgeStyle(displayBadge);

  return (
    <div className="collapsible-card">
      {/* Badge at the top if present */}
      {displayBadge && (
        <div 
          className={`badge badge-${displayBadge.toLowerCase().replace(/\s+/g, '-')}`}
          style={{
            ...badgeStyle,
            display: 'inline-block',
            padding: '4px 12px',
            borderRadius: '4px',
            fontSize: '0.75rem',
            fontWeight: '600',
            marginBottom: '8px',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}
        >
          {displayBadge}
        </div>
      )}
      
      <button
        className={`collapsible-header ${isOpen ? "open" : ""}`}
        onClick={handleToggle}
        aria-expanded={isOpen}
        style={{ width: '100%' }}
      >
        <span>{title}</span>
        <span className="collapsible-icon">{isOpen ? "−" : "+"}</span>
      </button>

      {/* Always render content in DOM, use CSS for visibility */}
      <div className={`collapsible-content ${isOpen ? 'open' : 'closed'}`}>
        {renderContent(content)}
      </div>
    </div>
  );
}

export default CollapsibleCard;
