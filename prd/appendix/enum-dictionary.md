# Appendix: Enum Dictionary

All enumerated types, status codes, and constant mappings used across the StudentLID codebase.

---

## User Roles

| Value | String | Notes |
|-------|--------|-------|
| `UserRole.STUDENT` | `"student"` | Default role for new registrations |
| `UserRole.TEACHER` | `"teacher"` | Instructor accounts |
| `UserRole.ADMIN` | `"admin"` | Defined but not actively used in current implementation |

---

## VARK Learning Styles

| Style | String Key | Description |
|-------|------------|-------------|
| Visual | `"Visual"` | Prefers graphical/visual information (diagrams, charts, videos) |
| Aural | `"Aural"` | Prefers auditory information (listening, discussing, verbal explanation) |
| Read/Write | `"Read/Write"` | Prefers written information (notes, lists, textbooks) |
| Kinesthetic | `"Kinesthetic"` | Prefers hands-on learning (experiments, real-world practice) |

---

## Honey & Mumford Learning Styles

| Style | String Key | Description |
|-------|------------|-------------|
| Activist | `"Activist"` | Learns by doing, jumping in, brainstorming |
| Reflector | `"Reflector"` | Learns by observing, reviewing, gathering data before acting |
| Theorist | `"Theorist"` | Learns by understanding underlying logic and building frameworks |
| Pragmatist | `"Pragmatist"` | Learns by applying theory to practical, real-world problems |

---

## Theme Modes

| Value | String | Notes |
|-------|--------|-------|
| Light | `"light"` | Default light theme |
| Calm | `"calm"` | Alternate "calm" theme variant |
| Contrast | `"contrast"` | High-contrast accessibility-oriented theme |

---

## Department Codes (Email Parsing)

Used by `ScoringService.get_student_email_profile()` to extract department from student email prefixes.

| Code | Department Name | Degree Type |
|------|----------------|-------------|
| `ise` | Information Science and Engineering | B.Tech. |
| `cs` | Computer Science | B.Tech. |
| `ad` | Artificial Intelligence and Data Science | B.Tech. |
| `al` | Artificial Intelligence and Machine Learning | B.Tech. |
| `cd` | Computer Science and Design | B.Tech. |
| `ag` | Agricultural Engineering | B.Tech. |
| `bm` | Biomedical Engineering | B.Tech. |
| `bt` | Biotechnology | B.Tech. |
| `ce` | Civil Engineering | B.E. |
| `cb` | Computer Science and Business Systems | B.Tech. |
| `ct` | Computer Technology | B.Tech. |
| `ee` | Electrical and Electronics Engineering | B.E. |
| `ec` | Electronics and Communication Engineering | B.E. |
| `ei` | Electronics and Instrumentation Engineering | B.E. |
| `ft` | Fashion Technology | B.Tech. |
| `fd` | Food Technology | B.Tech. |
| `it` | Information Technology | B.E. |
| `me` | Mechanical Engineering | B.E. |
| `mz` | Mechatronics Engineering | B.E. |
| `tt` | Textile Technology | B.E. |

**Email Pattern:** `{department_code}{2-digit-year}@university.edu` (e.g., `cs21@uni.edu` → CS, 2021 join year)

---

## Supported File Upload Extensions

| Extension | MIME Type | Processing Method |
|-----------|-----------|------------------|
| `.pdf` | application/pdf | PyPDF2 text extraction |
| `.docx` | application/vnd.openxmlformats-officedocument.wordprocessingml.document | python-docx paragraph extraction |
| `.txt` | text/plain | UTF-8 decode |
| `.png` | image/png | Gemini vision OCR + analysis |
| `.jpg` | image/jpeg | Gemini vision OCR + analysis |
| `.jpeg` | image/jpeg | Gemini vision OCR + analysis |
| `.webp` | image/webp | Gemini vision OCR + analysis |
| `.bmp` | image/bmp | Gemini vision OCR + analysis |
| `.gif` | image/gif | Gemini vision OCR + analysis |

---

## AI Provider Models

| Provider | Model | Use Case |
|----------|-------|----------|
| Google Gemini | `gemini-3` | Primary LLM for agents; web search grounding |
| Google Gemini | `gemini-2.5-flash` | Image analysis (vision) for uploaded images |
| Google Gemini Embeddings | `models/embedding-001` | FAISS vector store embeddings |
| Groq | `llama-3.3-70b-versatile` | Primary fallback; fast inference |
| Groq | `llama-3.1-8b-instant` | Secondary fallback model candidate |

---

## Chat Message Limits

| Limit | Value | Notes |
|-------|-------|-------|
| Max messages per thread | `100` | Oldest messages evicted when exceeded |
| Max user message length | `4000` chars | User messages truncated at this limit |
| Max assistant message length | `12000` chars | AI responses truncated at this limit |
| Max history for AI context | `8` messages | Last 8 turns sent to AI agent |
| Max title length | `80` chars | Thread titles truncated at this length |

---

## Password Reset Constants

| Constant | Value | Notes |
|---------|-------|-------|
| `PASSWORD_RESET_TTL_MINUTES` | `60` | Token expiry time in minutes |
| Token length | 32 bytes (URL-safe base64, ~43 chars) | Generated via `secrets.token_urlsafe(32)` |
| Hash algorithm | HMAC-SHA256 | Token hashed with `settings.SECRET_KEY` as the HMAC key |
| Minimum new password length | `8` characters | Enforced on reset password form |

---

## Pydantic Schemas

### User Schemas

| Schema | Fields | Notes |
|--------|--------|-------|
| `UserBase` | `email: EmailStr` | Shared base properties |
| `UserCreate` | `email`, `password` (min 8), `role` | Used for local registration |
| `UserResponse` | `email`, `name`, `role` | Never includes password |
| `PasswordResetRequest` | `email: EmailStr` | Request a password reset link |
| `PasswordResetConfirm` | `token`, `password`, `confirm_password` | Confirm password reset (min 8 chars each) |

---

## HTTP Status Codes (API Endpoints)

| Code | Meaning | Used Where |
|------|---------|------------|
| 200 | OK | Successful JSON responses |
| 302 | Found | Redirect responses (POST-result redirects) |
| 400 | Bad Request | Missing/invalid JSON fields, validation errors |
| 401 | Unauthorized | Missing or invalid JWT cookie |
| 403 | Forbidden | Role mismatch (e.g., student accessing teacher endpoint) |
| 404 | Not Found | Conversation thread not found |
| 500 | Internal Server Error | AI generation failure, email dispatch failure |

---

## Cookie Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Cookie name | `access_token` | Contains JWT bearer token |
| `HttpOnly` | `True` | Not accessible via JavaScript |
| `SameSite` | `lax` | CSRF-safe for same-site requests |
| `max_age` | `1800` seconds (30 minutes) | Session expiry |

---

## MongoDB Collections

| Collection | Document Type | Notes |
|------------|---------------|-------|
| `users` | `User` | Email-indexed; includes `password_reset_token_hash` and `password_reset_expires_at` for password reset |
| `classes` | `Class` | Code-indexed (unique) |
| `enrollments` | `Enrollment` | Compound index on (student_email, class_code) |
| `assessments` | `Assessment` | user_email + created_at sort |
| `conversation_threads` | `ConversationThread` | owner_email + owner_role indexed |
| `materials` | `Material` | Stores uploaded file metadata and extracted text |
