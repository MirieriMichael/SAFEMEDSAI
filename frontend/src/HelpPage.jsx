// frontend/src/HelpPage.jsx
import React, { useState } from 'react';
import './HelpPage.css';

const FAQItem = ({ question, answer }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className={`faq-item ${isOpen ? 'open' : ''}`} onClick={() => setIsOpen(!isOpen)}>
      <div className="faq-question">
        {question}
        <span className="material-symbols-outlined">{isOpen ? 'expand_less' : 'expand_more'}</span>
      </div>
      {isOpen && <div className="faq-answer">{answer}</div>}
    </div>
  );
};

export default function HelpPage() {
  return (
    <div className="help-page-container">
      
      <section className="help-header">
        <h1>Help & FAQ</h1>
        <p>Your guide to using SafeMedsAI effectively.</p>
      </section>

      <div className="help-content">
        {/* --- HOW TO USE SECTION --- */}
        <section className="how-to-section">
          <h2>How to Use SafeMedsAI</h2>
          <div className="steps-grid">
            <div className="step-card">
              <div className="step-icon">1</div>
              <h3>Upload or Type</h3>
              <p>Take a clear photo of your medication labels using the "Interaction Checker", or manually type the drug names (e.g., "Panadol, Aspirin").</p>
            </div>
            <div className="step-card">
              <div className="step-icon">2</div>
              <h3>AI Analysis</h3>
              <p>Our system uses OCR to read the label and AI to check our database for potential interactions between the drugs found.</p>
            </div>
            <div className="step-card">
              <div className="step-icon">3</div>
              <h3>Get Results</h3>
              <p>Receive a clear, layperson-friendly report. If you have a profile, we also check against your specific allergies.</p>
            </div>
          </div>
        </section>

        {/* --- FAQ SECTION --- */}
        <section className="faq-section">
          <h2>Common Questions</h2>
          
          <FAQItem 
            question="Is this tool a substitute for a doctor?" 
            answer="No. SafeMedsAI is an educational tool designed to provide information. It does not provide medical diagnoses or dosage recommendations. Always consult a healthcare professional before making decisions about your medication." 
          />
          <FAQItem 
            question="What if the OCR fails to read my label?" 
            answer="Ensure the image is clear, well-lit, and the text is horizontal. If the system cannot read the image, you can always use the 'Manual Entry' box to type the drug names directly." 
          />
          <FAQItem 
            question="How is my data protected?" 
            answer="We prioritize your privacy. Your scan history is stored securely and can be deleted by you at any time in your Profile. We do not share your personal health data with third parties." 
          />
          <FAQItem 
            question="Does this cover all drugs in Kenya?" 
            answer="Our database is optimized for medications commonly available in the Kenyan market, including many local brands. However, some rare or herbal medications may not yet be indexed." 
          />
          <FAQItem 
            question="What do the severity levels mean?" 
            answer="Major means the combination can be dangerous and requires immediate attention. Moderate means it may cause health risks or side effects. Minor means the interaction is unlikely to cause harm but should be monitored." 
          />
        </section>

        {/* --- NEW: CONTACT SECTION --- */}
        <section className="contact-section">
          <div className="contact-card">
            <h2>Still Confused?</h2>
            <p>Our support team is ready to assist you with any issues.</p>
            <a href="mailto:fromsafemedsai@gmail.com" className="contact-button">
              <span className="material-symbols-outlined">mail</span>
              Contact Support
            </a>
          </div>
        </section>
        {/* --- END NEW --- */}

      </div>
    </div>
  );
}