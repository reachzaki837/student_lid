# Appendix: Page Relationships

Navigation map and data flows between pages across the StudentLID application.

---

## Entry Points

| Route | Access | Description |
|-------|--------|-------------|
| `/` | Public | Redirects to `/auth/login` |
| `/auth/login` | Public | Login page; also Google OAuth entry |
| `/auth/register` | Public | Registration page; Google OAuth callback target |
| `/auth/forgot-password` | Public | Request password reset link |
| `/auth/reset-password` | Public | Reset password with token |

---

## Authentication Flow

```
[Root /] ──► /auth/login
                  │
                  ├── [Login Form POST] ──► /dashboard
                  │                              │
                  │◄── /auth/logout             │
                  │                              │
                  ├── [Register Link] ──► /auth/register ──► /auth/login
                  │
                  ├── [Forgot Password] ──► /auth/forgot-password ──► [Email with reset link]
                  │                                                        │
                  │                                                        ▼
                  │                                               [Click reset link in email]
                  │                                                        │
                  │                                                        ▼
                  │                                              /auth/reset-password?token=XXX
                  │                                                        │
                  │                                                        ▼
                  │                                           [Enter new password + confirm]
                  │                                                        │
                  │                                                        ▼
                  │                                            POST /auth/reset-password ──► /auth/login
                  │
                  └── [Google Button] ──► Google OAuth ──► /auth/google/callback
                                                                    │
                                      ┌─────────────────┴─────────────┐
                                      │                               │
                                 [Existing User]               [New User]
                                 JWT → /dashboard               Pre-fill → /auth/register
                                                                   │
                                                                   └──► /dashboard (after register)
```

---

## Student Flow

```
/auth/login ──► POST ──► /dashboard (student view)
                              │
                              ├── [No Assessment]
                              │    └──► /assessment/
                              │              │
                              │              └──► POST /assessment/submit ──► /dashboard
                              │
                              ├── [Has Assessment]
                              │    └──► Student Dashboard (persona + recommendations + radar chart)
                              │              │
                              │              ├── [Join Class] ──► POST /dashboard/join_class ──► /dashboard
                              │              │
                              │              ├── [AI Study Tutor] ──► /dashboard/tutor ──► POST /dashboard/chat_student
                              │              │                                    │
                              │              │◄───────────────────────────────────┘
                              │              │
                              │              ├── [Settings] ──► /dashboard/settings
                              │              │                  │
                              │              │◄─────────────────┘
                              │              │
                              │              └──► /auth/logout ──► /auth/login
                              │
                              └── [Has Assessment] + [AI Tutor] ◄──────────────────────┘
```

---

## Teacher Flow

```
/auth/login ──► POST ──► /dashboard (teacher view)
                              │
                              ├── [Dashboard Tab]
                              │    ├── [View Class Stats + Student Table]
                              │    ├── [Reset Assessment] ──► POST /dashboard/reset_assessment ──► /dashboard
                              │    ├── [Remove Student] ──► POST /dashboard/remove_student ──► /dashboard
                              │    ├── [Delete Class] ──► POST /dashboard/delete_class ──► /dashboard
                              │    ├── [Compose Email] ──► POST /dashboard/send_email ──► /dashboard
                              │    ├── [Export] ──► Client-side (PDF/CSV/Excel/JSON)
                              │    └── [Open AI Chatbot] ──► POST /dashboard/chat
                              │                                   │
                              │◄──────────────────────────────────┘
                              │
                              ├── [My Classes Tab]
                              │    ├── [Create Class] ──► POST /dashboard/create_class ──► /dashboard
                              │    └── [Add Students] ──► POST /dashboard/manual_enroll ──► /dashboard
                              │
                              ├── [AI Assistant Page] ──► /dashboard/assistant ──► POST /dashboard/chat
                              │
                              ├── [Settings] ──► /dashboard/settings
                              │
                              └──► /auth/logout ──► /auth/login
```

---

## Data Coupling Across Pages

| Data | Shared Across | How |
|------|--------------|-----|
| User session | All authenticated pages | JWT cookie validated on every request via `get_current_user()` |
| Assessment results | Dashboard, AI Tutor | Fetched fresh from MongoDB on each page load |
| Enrollments | Student Dashboard, Teacher Dashboard | MongoDB Enrollment collection |
| Class codes | Teacher: Create/Enroll; Student: Join | `Class.code` — randomly generated 6-char string |
| Teacher stats (stats_str) | Teacher Dashboard, `/dashboard/chat` | Rebuilt from DB on each chat request |
| Conversation threads | Chat endpoints | `ConversationThread` documents in MongoDB |
| FAISS vector store | Document upload, Chat tools | File persisted to `/tmp/faiss_index` |
| Email profile | Student Dashboard, Settings | Parsed from email on each load (not persisted) |

---

## Assessment Lifecycle

```
[Student Registers] ──► /auth/register
        │
        ▼
[Student Logs In] ──► /auth/login ──► POST ──► /dashboard (no assessment state)
        │
        ▼
[Start Assessment] ──► /assessment/ ──► [Answer 8 questions]
        │
        ▼
[Submit] ──► POST /assessment/submit
        │      Creates Assessment doc in MongoDB
        ▼
[Redirect to Dashboard] ◄── /dashboard (has assessment state)
        │
        ├──► View persona + recommendations + radar chart
        ├──► Chat with AI Tutor ──► Agent uses assessment for style context
        └──► Retake? ──► [Submit again] ──► Creates NEW Assessment doc
                              (old ones remain; dashboard shows most recent)
```

---

## Document Upload → AI Chat Flow

```
[Teacher uploads file] ──► POST /dashboard/upload_document
        │                  1. Extract text (PDF/DOCX/TXT/Gemini Vision)
        │                  2. Save Material doc to MongoDB
        │                  3. Chunk text
        │                  4. Add to FAISS index
        ▼
[Teacher chats] ──► POST /dashboard/chat
        │
        └──► AgentService.get_teacher_agent_response()
                   │
                   ├──► search_uploaded_course_materials(query)
                   │        │
                   │        └──► RAGService.query_documents()
                   │                   │
                   │                   └──► FAISS.similarity_search() ──► Returns chunks
                   │
                   ├──► search_web(query) ──► DuckDuckGo via ddgs
                   │
                   ├──► search_youtube(query) ──► DuckDuckGo video search
                   │
                   └──► send_email_to_student(...) ──► Gmail SMTP
```
