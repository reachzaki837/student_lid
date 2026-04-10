# StudentLID — Product Requirements Document

## System Overview

StudentLID is an AI-powered educational platform that identifies student learning styles using two established pedagogical frameworks — **VARK** (Visual, Aural, Read/Write, Kinesthetic) and **Honey & Mumford** (Activist, Reflector, Theorist, Pragmatist) — and delivers personalized study recommendations through generative AI. The platform serves two primary user roles: **students** who take assessments and receive AI tutoring, and **teachers** who manage classes, view analytics, and use an AI teaching assistant.

Students sign up or log in, complete a multi-question learning style assessment (4 VARK questions + 4 Honey & Mumford questions), and are assigned a dominant learning persona expressed as a combination (e.g., "Visual Activist"). The system generates AI-powered study tips, tool recommendations, and scheduling advice tailored to their specific combination. Students can join classes via invite codes, access an AI Study Tutor that adapts explanations to their learning style, and chat with an agent that searches the web and YouTube for educational content.

Teachers create and manage classes, each identified by a unique 6-character alphanumeric code. They can manually enroll students by email, view which students have completed assessments and what their dominant styles are, see aggregate learning style distributions across their cohort, and send email broadcasts to entire classes or selected students. Teachers also have access to a draggable/resizable AI Teaching Assistant chatbot that provides Perplexity-style research responses informed by the teacher's real classroom data (class size, dominant styles, active students). Teachers can upload course materials (PDF, DOCX, TXT, images) which are indexed into a FAISS vector store for retrieval-augmented generation (RAG) so the AI can answer questions from uploaded content.

The system is built on **FastAPI** with **MongoDB/Beanie ODM**, server-rendered **Jinja2 HTML templates**, and **LangChain ReAct agents** backed by **Google Gemini** (primary) and **Groq LLaMA** (fallback). Authentication supports both local email/password registration and **Google OAuth 2.0**.

---

## Module Overview

| Module | Pages | Core Functionality |
|--------|-------|--------------------|
| Authentication | Login, Register, Forgot Password, Reset Password | Email/password login, Google OAuth sign-in, user registration with role selection (student/teacher), password reset via email link |
| Assessment | Assessment Form | 8-question VARK + Honey & Mumford questionnaire with step-by-step UI, progress bar, and animated transitions |
| Student Dashboard | Student Home, AI Tutor | View learning persona, personalized study recommendations (tips, tools, schedule), radar chart of VARK scores, join class by code |
| Teacher Dashboard | Teacher Home, AI Assistant, Settings | Class management (create/delete), student roster with style badges, aggregate bar chart, embedded draggable chatbot, email composer with student selection, settings management |
| Settings | Profile/Password/Preferences | Update display name, department, degree, semester; change password; set theme mode (light/calm/contrast), notifications, weekly digest, focus mode |

---

## Page Inventory

| # | Page Name | Route | Module | Doc Link |
|---|-----------|-------|--------|----------|
| 1 | Login | `/auth/login` | Auth | [→](./pages/01-auth-login.md) |
| 2 | Register | `/auth/register` | Auth | [→](./pages/02-auth-register.md) |
| 3 | Forgot Password | `/auth/forgot-password` | Auth | [→](./pages/03-auth-forgot-password.md) |
| 4 | Reset Password | `/auth/reset-password` | Auth | [→](./pages/04-auth-reset-password.md) |
| 5 | Learning Assessment | `/assessment/` | Assessment | [→](./pages/05-assessment-form.md) |
| 6 | Student Dashboard | `/dashboard` | Student | [→](./pages/06-student-dashboard.md) |
| 7 | AI Study Tutor | `/dashboard/tutor` | Student | [→](./pages/07-student-tutor.md) |
| 8 | Teacher Dashboard | `/dashboard` | Teacher | [→](./pages/08-teacher-dashboard.md) |
| 9 | AI Teaching Assistant | `/dashboard/assistant` | Teacher | [→](./pages/09-teacher-assistant.md) |
| 10 | Account Settings | `/dashboard/settings` | Settings | [→](./pages/10-settings.md) |

---

## Global Notes

### Permission Model
- **Role-based access control** via `UserRole` enum: `STUDENT`, `TEACHER`, `ADMIN`
- JWT session cookies (`HttpOnly`, 30-minute max age) store authenticated sessions
- Teacher-only routes check `user.role == "teacher"`; student-only routes check `user.role == "student"`
- Google OAuth callback distinguishes new vs. existing users — new users are pre-filled into the registration flow

### Common Interaction Patterns
- All form submissions use server-side rendering with redirect-after-post pattern
- API endpoints (chat, email, document upload) return JSON responses
- Class codes are 6-character alphanumeric strings generated randomly
- Assessment can be reset by teachers; subsequent submissions overwrite previous results
- Chat conversations are persistent (stored in MongoDB) with title auto-generated from first message
- Teachers see all students across all their classes (not per-class filtering in current implementation)
- Student email profiles (department, degree, academic progress) are auto-parsed from their email address via regex pattern matching against known Indian engineering department codes

### Password Reset Flow
- Token-based reset: server generates a cryptographically random URL-safe token (`secrets.token_urlsafe(32)`), stores only its HMAC-SHA256 hash in `User.password_reset_token_hash`, and sets an expiry (`User.password_reset_expires_at`, 60 minutes TTL)
- The raw token is sent to the user's email address; only the hash is stored — never the plaintext token
- The reset link is single-use: after a successful password change, both `password_reset_token_hash` and `password_reset_expires_at` are cleared from the user document
- Google OAuth accounts (no local password) return silently on the forgot-password request to prevent account enumeration
- A **dev-only preview endpoint** `/auth/dev/email-preview/reset-password` renders the branded HTML email body without sending it; it is gated to `ENVIRONMENT ∈ {development, dev, local, test}`

### AI Provider Fallback Chain
1. Primary: Google Gemini (`gemini-3` with web search grounding)
2. Fallback: Groq LLaMA (`llama-3.3-70b-versatile`)
3. Graceful degradation with user-facing error messages for 429/503/timeout errors

### Department Code Parsing
The system parses student email prefixes to extract department information. Supported codes include `ise` (Information Science and Engineering), `cs` (Computer Science), `ad` (AI & Data Science), etc. Academic year and semester are computed from the join year embedded in the email and the current date.
