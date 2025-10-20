// frontend/src/FormattedText.jsx
import React from 'react';

function FormattedText({ text }) {
  if (!text || text === 'No information available.') {
    return <p>{text}</p>;
  }
  // This splits the text by newlines or common medical headings
  const sections = text.split(/\n|(?=WARNINGS:|ADVERSE REACTIONS:|DOSAGE AND ADMINISTRATION:)/i);
  return (
    <div className="formatted-text">
      {sections.map((section, index) => {
        const trimmedSection = section.trim();
        if (trimmedSection) {
          // Makes headings bold for readability
          if (/^(WARNINGS:|ADVERSE REACTIONS:|DOSAGE AND ADMINISTRATION:)/i.test(trimmedSection)) {
            return <p key={index}><strong>{trimmedSection}</strong></p>;
          }
          return <p key={index}>{trimmedSection}</p>;
        }
        return null;
      })}
    </div>
  );
}
export default FormattedText;