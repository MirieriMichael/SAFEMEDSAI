// // frontend/src/CollapsibleCard.jsx
// import React, { useState } from 'react';

// function CollapsibleCard({ title, content }) {
//   const [isOpen, setIsOpen] = useState(false);

//   // If there's no content to display, show a simple placeholder and don't make it a button.
//   if (!content || content === 'No information available.') {
//     return (
//         <div className="collapsible-card-static">
//             <strong>{title}:</strong> N/A
//         </div>
//     );
//   }

//   return (
//     <div className="collapsible-card">
//       <button className="collapsible-header" onClick={() => setIsOpen(!isOpen)}>
//         <span>{title}</span>
//         <span className="collapsible-icon">{isOpen ? '−' : '+'}</span>
//       </button>
//       {isOpen && (
//         <div className="collapsible-content">
//           {/* This handles content that might have multiple lines */}
//           {content.split('\n').map((paragraph, index) => (
//             paragraph.trim() && <p key={index}>{paragraph.trim()}</p>
//           ))}
//         </div>
//       )}
//     </div>
//   );
// }

// export default CollapsibleCard;
import React, { useState } from 'react';

function CollapsibleCard({ title, content, children }) {
  const [isOpen, setIsOpen] = useState(false);

  // Normalize content: use children if provided, otherwise use content prop
  const displayContent = children || content;

  // If there's no content to display, show a simple placeholder.
  if (!displayContent || (typeof displayContent === 'string' && (displayContent.trim() === '' || displayContent === 'No information available.'))) {
    return (
        <div className="collapsible-card-static" style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #374151', color: '#9ca3af', fontSize: '0.9rem' }}>
            <strong>{title}:</strong> <span style={{marginLeft:'8px'}}>No information provided.</span>
        </div>
    );
  }

  // Render content based on type
  const renderContent = () => {
    if (typeof displayContent === 'string') {
      // Split by newlines and render each paragraph
      const paragraphs = displayContent.split('\n').filter(p => p.trim());
      if (paragraphs.length === 0) {
        return <div style={{ color: '#e5e7eb', padding: '10px 0' }}>No information provided.</div>;
      }
      return paragraphs.map((paragraph, index) => (
        <p key={index} style={{ color: '#e5e7eb', margin: '5px 0', lineHeight: '1.5' }}>
          {paragraph.trim()}
        </p>
      ));
    }
    // If content is JSX or React element, render it directly
    return displayContent;
  };

  return (
    <div className="collapsible-card">
      <button 
        className={`collapsible-header ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls={`collapsible-content-${title.replace(/\s+/g, '-').toLowerCase()}`}
      >
        <span>{title}</span>
        <span className="collapsible-icon">{isOpen ? '−' : '+'}</span>
      </button>
      
      {isOpen && (
        <div 
          className="collapsible-content open"
          id={`collapsible-content-${title.replace(/\s+/g, '-').toLowerCase()}`}
          style={{ 
            display: 'block',
            color: '#e5e7eb',
            padding: '10px 0',
            visibility: 'visible',
            opacity: 1
          }}
        >
          {renderContent()}
        </div>
      )}
    </div>
  );
}

export default CollapsibleCard;