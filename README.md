# SafeMedsAI 💊🛡️

> **A Neuro-Symbolic Drug Interaction Checker tailored for the Kenyan Healthcare Context.**

![Status](https://img.shields.io/badge/Status-Prototype-orange)
![Python](https://img.shields.io/badge/Backend-Django-blue)
![React](https://img.shields.io/badge/Frontend-React-61DAFB)
![AI](https://img.shields.io/badge/AI-Mistral%20%2F%20Groq-purple)

## 📖 About The Project

**SafeMedsAI** is a final-year Computer Science project designed to prevent adverse drug events (ADEs) in low-resource settings. unlike generic international tools (like WebMD), SafeMedsAI is built to understand **local Kenyan drug brands** (e.g., *Mara Moja*, *Dawanol*) and bridge the gap between complex medical data and rural patients.

It combines **OCR (Optical Character Recognition)** to scan physical prescriptions with **LLMs (Large Language Models)** to provide easy-to-understand safety summaries in English (and potential for Swahili).

### Key Features
* 📷 **Smart Prescription Scanning:** Uses Tesseract OCR & OpenCV to extract drug names from photos of handwritten or printed prescriptions.
* 🇰🇪 **Local Brand Recognition:** Includes a custom mapping layer that translates Kenyan trade names (e.g., *Beta-Pyin*) into their generic chemical equivalents (e.g., *Aspirin*) for accurate analysis.
* 🧠 **Neuro-Symbolic AI Engine:**
    * **Symbolic:** Hard-coded safety checks against known contraindications (High Accuracy).
    * **Neural:** Generative AI (Mistral-7B via Groq) to explain risks in simple, non-medical language.
* ⚡ **Fast & Lightweight:** Optimized for low-bandwidth environments common in rural clinics.

---

## 🛠️ Tech Stack

* **Backend:** Django (Python), Django REST Framework
* **Frontend:** React.js, Tailwind CSS
* **Database:** PostgreSQL
* **AI/ML:** OpenCV, Tesseract OCR, Groq API (Mistral/Llama3), LangChain
* **DevOps:** Docker (Optional), Git

---

## 🚀 Getting Started

Follow these steps to set up the project locally.

### Prerequisites
* Python 3.9+
* Node.js & npm
* **Tesseract OCR** (System Requirement):
    * *Windows:* [Download Installer](https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH.
    * *Linux:* `sudo apt-get install tesseract-ocr`
    * *Mac:* `brew install tesseract`

### 1. Backend Setup (Django)

```bash
# Clone the repo
git clone [https://github.com/yourusername/SafeMedsAI.git](https://github.com/yourusername/SafeMedsAI.git)
cd SafeMedsAI/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
# (Add your GROQ_API_KEY and DATABASE_URL inside .env)

# Run migrations
python manage.py migrate

# Start the server
python manage.py runserver

```

### 2. Frontend Setup (React)

```bash
# Open a new terminal and navigate to frontend
cd ../frontend

# Install node modules
npm install

# Start the development server
npm start

```

Your app should now be running at `http://localhost:3000`!

---

## 📸 Usage Guide

1. **Dashboard:** Log in as a Patient or Pharmacist.
2. **Scan:** Click "Upload Prescription" and take a photo of the medicine box or prescription paper.
3. **Verify:** The OCR will extract text. Manually correct any typos if the image was blurry.
4. **Analyze:** Click "Check Interactions."
5. **Result:**
* **Red Flag:** Dangerous interaction found (e.g., "Do not take Warfarin with Aspirin").
* **AI Explanation:** "Taking these together might increase bleeding risk. Please consult your doctor."



---

## 🔮 Roadmap & Future Improvements

* [ ] **Offline PWA:** Enable caching for usage in remote areas without internet.
* [ ] **WhatsApp Bot:** Integration via Twilio for SMS-based checking.
* [ ] **Voice Support:** Text-to-Speech for visually impaired or low-literacy users.
* [ ] **Swahili Translation:** Fine-tuning the model to output safety warnings in Kiswahili.

---


## 📄 License
**Copyright © 2026 Michael Mirieri. All Rights Reserved.**

This project is proprietary and confidential. Unauthorized copying, distribution, or modification 
of this file or project, via any medium, is strictly prohibited.

Permission is granted for academic evaluation and recruitment viewing only.

```



```
