# StudentLID: Student Learning Style Identification System

An AI-powered educational platform designed to identify how students learn best and provide actionable, data-driven insights to both learners and educators.

By combining established pedagogical frameworks (VARK and Honey & Mumford) with cutting-edge Generative AI, StudentLID transforms a simple quiz into a personalised learning engine.

---

## ❓ Why is this needed? (The Problem)

In a traditional classroom, a "one-size-fits-all" teaching approach inevitably leaves some students behind. A highly visual learner might struggle through a 45-minute audio lecture, while a kinesthetic learner might lose focus reading dense text.

**StudentLID solves this by:**
1. Helping students understand their own cognitive wiring so they can study smarter, not harder.
2. Giving teachers instant, bird's-eye visibility into the learning modalities of their classroom.
3. Reducing teacher burnout by using AI to automatically generate lesson plans tailored to the *actual* makeup of their students.

---

## ✨ Key Features

### 🔐 Authentication & Accounts

* **Email / Password Registration & Login** — Standard sign-up with server-side bcrypt-equivalent (pbkdf2_sha256) password hashing. Plaintext legacy passwords are transparently migrated to the secure hash on first login.
* **Google OAuth 2.0** — One-click sign-in with Google. Existing accounts are recognized and logged in automatically; new Google users are redirected to a pre-filled registration page to choose their role.
* **JWT Session Cookies** — Authenticated sessions are managed via an HttpOnly `access_token` cookie (30-minute expiry), preventing XSS-based token theft.
* **Role-Based Access Control** — Two roles are defined (`student`, `teacher`). Every dashboard route and API endpoint enforces the correct role before serving content.

---

### 🧑‍🎓 For Students

#### Learning Style Assessment
* **Dual-Framework Quiz** — Students complete a comprehensive assessment that measures:
  * **VARK** (Visual, Aural, Read/Write, Kinesthetic) — *how* a student best receives new information.
  * **Honey & Mumford** (Activist, Reflector, Theorist, Pragmatist) — *how* a student cognitively processes and applies that information.
* Scores are persisted to MongoDB and displayed on the student dashboard with a breakdown chart.

#### AI-Generated Study Strategy
* Upon completing the quiz, the platform calls the **Groq API** (model: `llama-3.3-70b-versatile` with `llama-3.1-8b-instant` as fallback) in **JSON Mode** to generate a fully personalized study plan, including:
  * **Actionable study tips** tailored to the exact VARK + Honey & Mumford combination.
  * **Recommended software tools** (e.g., Miro for Visual learners, Speechify for Aural, Labster for Kinesthetic).
  * **Ideal study schedule** matching the student's cognitive processing style (e.g., Pomodoro for Activists, 90-minute deep-focus blocks for Reflectors).
* A static rule-based fallback is used if the API is unavailable.

#### AI Study Tutor (ReAct Agent)
* A dedicated **Student AI Tutor** page powered by a LangChain ReAct agent.
* Primary LLM: **Google Gemini 2.5 Flash**; automatic fallback to **Groq LLaMA 3.3 70B** on quota/rate-limit errors.
* The tutor is **personalized to the student's VARK and HM profile** and uses three live tools on every query:
  * 🌐 **`search_web`** — DuckDuckGo real-time web search for up-to-date information and citations.
  * 📺 **`search_youtube`** — Finds relevant educational YouTube videos for the topic.
  * 📄 **`search_uploaded_course_materials`** — Semantic search over teacher-uploaded documents via FAISS RAG.
* Responses are formatted Perplexity-style with headers, citations, and a "Watch & Learn" video section.
* Conversation history (last 6 turns) is injected as context for follow-up questions.

#### Class Enrollment
* Join any active class by entering a **6-character alphanumeric invite code** on the dashboard.
* Enrolled classes and their names are displayed on the student home page.

#### Email-Inferred Academic Profile
* The system automatically parses the student's institutional email address to extract their **department code** and **join year**, then computes their current degree (B.E. or B.Tech.), batch, study year, and semester — no manual input required.
* Students (and teachers viewing the roster) can also manually override these details in Settings.

---

### 👩‍🏫 For Teachers

#### Class Management
* **Create Classes** — Generate a new class with a custom name; the system auto-assigns a unique 6-character invite code.
* **Manual Enrollment** — Teachers can add any registered students directly to their classes without waiting for the student to use an invite code.
* **Delete Classes** — Remove a class and all its enrollments in one action.

#### Classroom Analytics Dashboard
* Interactive **Chart.js pie/bar charts** visualizing the VARK learning style distribution across all active classes.
* Summary cards showing total active classes and total enrolled students.

#### Student Roster Management
* View a full roster with each student's name, email, department, degree, academic progress, dominant VARK style, and raw VARK/HM score breakdown.
* **Reset Assessment** — Clear a student's quiz results so they can retake the assessment.
* **Remove Student** — Unenroll a student from all of the teacher's classes.

#### 1-Click Data Exports
* Download the full classroom dataset instantly as:
  * 📄 **PDF** (via jsPDF)
  * 📊 **Excel / .xlsx** (via SheetJS)
  * 📋 **CSV**

#### Agentic AI Teaching Assistant
* A dedicated **Teacher AI Assistant** page with a full-screen, Perplexity-style research chatbot.
* The agent **reads live classroom stats** (total students, VARK distribution) before answering, enabling context-aware questions like *"How should I teach Newton's Laws to my class?"*
* Uses the same four tools as the student tutor, plus a fifth:
  * 📧 **`send_email_to_student`** — Send a personalized email directly to a specific student from within the chat interface.
* Primary LLM: **Google Gemini 2.5 Flash**; automatic fallback to **Groq LLaMA 3.3 70B**.

#### Email Broadcasting
* Send bulk emails to selected students directly from the teacher dashboard.
* Powered by **Gmail SMTP** with App Password authentication; dispatched asynchronously to avoid blocking the UI.

---

### 📁 Document Upload & RAG (Retrieval-Augmented Generation)

* Teachers (or any authenticated user) can upload course materials to feed the AI agents.
* **Supported formats:** PDF, TXT, DOCX, PNG, JPG, JPEG, WEBP, BMP, GIF.
* **Image analysis:** Image files are passed to **Gemini 2.5 Flash Vision** which extracts OCR text, key topics, formulas, and teaching cues before indexing.
* Text is chunked (`RecursiveCharacterTextSplitter`, 1000 chars / 200 overlap) and embedded using **Google Generative AI Embeddings** (`models/embedding-001`).
* Chunks are stored in a **FAISS** vector index (persisted to `/tmp/faiss_index` for Vercel compatibility).
* File metadata and raw text are also saved to MongoDB in the `materials` collection for auditing.

---

### ⚙️ User Settings

Available to both students and teachers at `/dashboard/settings`:

* **Profile** — Update display name; students can also set department, degree, and semester manually.
* **Password** — Change password with current-password verification and length enforcement (min. 6 chars). Not available for Google OAuth accounts.
* **Preferences** — Choose a UI **theme** (`light`, `calm`, `contrast`), toggle **email notifications**, **weekly digest**, and **focus mode**.

---

## 🏗️ Tech Stack & Architecture

StudentLID is built on a modern, asynchronous Python stack optimized for speed and real-time AI streaming.

| Layer | Technology |
|---|---|
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/) (async Python) |
| **Database** | [MongoDB](https://www.mongodb.com/) + [Beanie ODM](https://beanie-odm.dev/) + [Motor](https://motor.readthedocs.io/) |
| **Frontend** | HTML5, [Bootstrap 5](https://getbootstrap.com/), Jinja2, Vanilla JS |
| **AI — Primary** | [Google Gemini 2.5 Flash](https://deepmind.google/technologies/gemini/) via `langchain-google-genai` |
| **AI — Fallback** | [Groq](https://groq.com/) `llama-3.3-70b-versatile` / `llama-3.1-8b-instant` via `langchain-groq` |
| **Study Recommendations** | Groq API (JSON Mode enforced) with static rule-based fallback |
| **Agentic Framework** | [LangChain](https://www.langchain.com/) `create_tool_calling_agent` + `AgentExecutor` (ReAct) |
| **Vector Search (RAG)** | [FAISS](https://faiss.ai/) + Google Generative AI Embeddings |
| **Document Parsing** | PyPDF2, python-docx, Gemini Vision (images) |
| **Web Search** | DuckDuckGo Search (`ddgs`) |
| **Data Visualization** | [Chart.js](https://www.chartjs.org/) |
| **Markdown Rendering** | [Marked.js](https://marked.js.org/) |
| **Data Exports** | [SheetJS](https://sheetjs.com/) (Excel/CSV), [jsPDF](https://github.com/parallax/jsPDF) (PDF) |
| **Email** | Gmail SMTP (`smtplib`) dispatched via `asyncio.to_thread` |
| **Auth** | JWT (`python-jose`), bcrypt-equivalent hashing, Google OAuth 2.0 |
| **Deployment** | [Vercel](https://vercel.com/) (Python Serverless Runtime) |

---

## 📂 Project Structure

```
student_lid/
├── main.py                    # FastAPI app entry point, lifespan (MongoDB init)
├── requirements.txt
├── vercel.json                # Vercel deployment config
├── app/
│   ├── core/
│   │   ├── config.py          # Pydantic Settings (env vars)
│   │   └── security.py        # JWT creation, password hashing/verification
│   ├── db/
│   │   └── mongo.py           # Beanie init_db
│   ├── models/
│   │   └── user.py            # Beanie documents: User, Class, Enrollment, Assessment, Material
│   ├── routers/
│   │   ├── auth.py            # /auth/* — login, register, Google OAuth, logout
│   │   ├── dashboard.py       # /dashboard/* — student & teacher views, settings, chat
│   │   └── assessment.py      # /assessment/* — quiz form & submission
│   ├── schemas/               # Pydantic request/response schemas
│   ├── services/
│   │   ├── agent.py           # LangChain ReAct agents (teacher & student) + tool definitions
│   │   ├── auth.py            # User creation & authentication logic
│   │   ├── email.py           # Gmail SMTP email dispatch (sync + async wrapper)
│   │   ├── rag.py             # Document upload, FAISS indexing, RAG query
│   │   └── scoring.py         # VARK/HM scoring, email profile parser, Groq recommendations
│   ├── static/                # CSS, JS, images
│   └── templates/
│       ├── base.html
│       ├── auth/              # login.html, register.html
│       ├── assessment/        # form.html
│       └── dashboard/         # student.html, teacher.html, teacher_assistant.html,
│                              #   student_chat.html, settings.html
└── tests/
    └── test_security_auth.py  # Pytest: password hashing, auth flow
```

---

## 🔑 Environment Variables

Create a `.env` file in the project root with the following keys:

```dotenv
# ── Core ──────────────────────────────────────────────────
SECRET_KEY=<a-long-random-string>        # JWT signing key
ENVIRONMENT=development                  # set to "production" on live deployments
DATABASE_URL=mongodb://localhost:27017   # MongoDB connection string
DATABASE_NAME=learning_app_db

# ── AI Providers (at least one required) ──────────────────
GOOGLE_API_KEY=<your-google-ai-api-key>  # Gemini 2.5 Flash + Embeddings
GROQ_API_KEY=<your-groq-api-key>         # LLaMA 3.3 70B / 3.1 8B (fallback)

# ── Google OAuth (optional — enables "Sign in with Google") ─
GOOGLE_CLIENT_ID=<your-oauth-client-id>
GOOGLE_CLIENT_SECRET=<your-oauth-client-secret>

# ── Gmail Email Dispatch (optional — enables email features) ─
GMAIL_SENDER_EMAIL=your-address@gmail.com
GMAIL_APP_PASSWORD=<gmail-app-password>  # NOT your Gmail login password
```

> **Note:** `GOOGLE_API_KEY` is required for image uploads (Gemini Vision) and RAG embeddings. `GROQ_API_KEY` is required for the AI study recommendations on the student dashboard. Providing both enables automatic failover between providers.

---

## 🚀 Getting Started (Local Development)

**Prerequisites:** Python 3.11+, MongoDB running locally (or a MongoDB Atlas URI).

```bash
# 1. Clone the repository
git clone https://github.com/reachzaki837/student_lid.git
cd student_lid

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env          # then fill in your keys in .env

# 5. Start the development server
uvicorn main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) — you will be redirected to the login page.

---

## ☁️ Deployment (Vercel)

The project is pre-configured for **Vercel Python Serverless** deployment via `vercel.json`.

1. Push to GitHub and import the repository in the [Vercel dashboard](https://vercel.com/new).
2. Add all required environment variables in **Project → Settings → Environment Variables**.
3. Set `ENVIRONMENT=production` to enable strict secret validation on startup.
4. Set `DATABASE_URL` to a publicly reachable MongoDB Atlas connection string (localhost is blocked on Vercel).
5. Deploy — Vercel will use `main.py` as the serverless entry point.

> The app detects Vercel automatically via the `VERCEL` / `VERCEL_ENV` environment variables and skips the MongoDB startup check if no external database URL is configured, preventing cold-start crashes.

---

## 🧪 Running Tests

```bash
pytest tests/
```

The test suite covers password hashing, roundtrip verification, legacy plaintext password migration, and authentication rejection logic.

---

## 📄 License

This project is licensed under the terms of the [LICENSE](LICENSE) file included in this repository.
