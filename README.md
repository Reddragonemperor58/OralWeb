# OralDiag SaaS - AI-Powered Oral Diagnosis Platform

## 1. Project Overview
OralDiag SaaS is a web-based telemedicine platform designed for dentists. It combines traditional rule-based clinical diagnosis with modern AI image analysis.

The application uses a **Client-Server Architecture**:
* **Frontend (UI):** Built with **Streamlit**. Runs in the browser. Handles user inputs and displays results.
* **Backend (API):** Built with **FastAPI**. Handles security, database management, and AI processing.
* **AI Engine:** Uses **TensorFlow** (for cancer classification) and **Scikit-Image** (for SSIM texture comparison).

---

## 2. Directory Structure
This structure is modular to separate UI logic from Business logic.

```text
OralDiagnosisWeb/
│
├── backend/                # THE SERVER (FastAPI)
│   ├── main.py             # API Entry Point: Defines routes (/login, /analyze, etc.)
│   ├── auth.py             # Security: JWT Token generation & Password Hashing
│   ├── database.py         # DB Connection (SQLite for local, scalable to RDS)
│   ├── models.py           # SQL Table Definitions (Users, Patients)
│   ├── schemas.py          # Pydantic Models (Data Validation)
│   ├── analysis.py         # AI Logic: SSIM Calc & Deep Learning Prediction
│   └── oral_cancer_model.h5 # Pre-trained Keras Model (Required)
│
├── frontend/               # THE CLIENT (Streamlit)
│   ├── app.py              # Main UI Script: Login, Dashboard, Diagnosis Tabs
│   └── For new software pre Final 7.xlsx # Rule Engine for Clinical Diagnosis
│
├── requirements.txt        # Dependency List (See Version Notes below)
└── README.md               # Project Documentation