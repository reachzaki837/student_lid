# Appendix: API Inventory

Complete reference of all backend API endpoints (both HTML form/redirect and JSON responses).

---

## Authentication Endpoints

### `GET /auth/login`
- **Description:** Renders the login page
- **Auth required:** No
- **Query params:** `error` (optional) — error message to display

### `POST /auth/login`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Fields:** `email` (string), `password` (string)
- **Success:** Sets JWT HttpOnly cookie, redirects to `/dashboard` (302)
- **Failure:** Re-renders login page with error message
- **Auth required:** No

### `GET /auth/register`
- **Description:** Renders the registration page
- **Auth required:** No
- **Query params:** `google_name`, `google_email`, `google_id`, `google_picture` (optional, from OAuth flow)

### `POST /auth/register`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Fields:** `email` (string), `password` (string, optional), `role` (UserRole), `name` (string), `google_id` (string, optional), `google_picture` (string, optional)
- **Success (local):** Redirects to `/auth/login` (302)
- **Success (Google):** Sets JWT cookie, redirects to `/dashboard` (302)
- **Failure:** Re-renders register page with error
- **Auth required:** No

### `GET /auth/google`
- **Description:** Initiates Google OAuth 2.0 flow
- **Auth required:** No
- **Behavior:** Server-side 302 redirect to `https://accounts.google.com/o/oauth2/v2/auth`

### `GET /auth/google/callback`
- **Auth required:** No
- **Query params:** `code` (OAuth authorization code), `error` (optional)
- **Behavior:**
  - Exchanges code for tokens at `https://oauth2.googleapis.com/token`
  - Fetches user info from `https://www.googleapis.com/oauth2/v3/userinfo`
  - If existing user: creates JWT, redirects to `/dashboard`
  - If new user: redirects to `/auth/register` with pre-filled Google data
  - On error: redirects to `/auth/login?error=...`

### `GET /auth/logout`
- **Description:** Clears JWT cookie and redirects to login
- **Auth required:** No

---

## Assessment Endpoints

### `GET /assessment/`
- **Description:** Renders the step-by-step assessment questionnaire
- **Auth required:** Yes (any role)

### `POST /assessment/submit`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Fields:** `vark_1`, `vark_2`, `vark_3`, `vark_4`, `hm_1`, `hm_2`, `hm_3`, `hm_4` (all string, one value each)
- **Success:** Creates `Assessment` document, redirects to `/dashboard` (302)
- **Auth required:** Yes (any role)

---

## Dashboard Endpoints

### `GET /dashboard`
- **Description:** Renders student or teacher dashboard based on `user.role`
- **Auth required:** Yes
- **Teacher data loaded:** Classes, enrollments, student_data (with assessments), style_counts, all_students
- **Student data loaded:** Assessment, recommendations (AI or fallback), enrolled classes, email_profile

### `GET /dashboard/settings`
- **Description:** Renders the account settings page
- **Auth required:** Yes
- **Query params (feedback):** `profile_success`, `profile_error`, `password_success`, `password_error`, `prefs_success`, `prefs_error`

### `POST /dashboard/update_profile`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Fields:** `name` (string, required), `department` (string, optional), `degree` (string, optional), `semester` (string, optional)
- **Success:** Updates User document, redirects to `/dashboard/settings?profile_success=...`
- **Failure:** Redirects to `/dashboard/settings?profile_error=...`
- **Auth required:** Yes

### `POST /dashboard/update_password`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Fields:** `current_password`, `new_password`, `confirm_password`
- **Success:** Updates password hash, redirects to `/dashboard/settings?password_success=...`
- **Failure:** Redirects with error in query string
- **Auth required:** Yes

### `POST /dashboard/update_preferences`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Fields:** `theme_mode` (string: light/calm/contrast), `notifications_enabled` (on/off), `weekly_digest` (on/off), `focus_mode` (on/off)
- **Success:** Updates User document, redirects to `/dashboard/settings?prefs_success=...`
- **Failure:** Redirects with error
- **Auth required:** Yes

### `POST /dashboard/create_class`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Fields:** `name` (string)
- **Success:** Creates Class document (6-char random code), redirects to `/dashboard`
- **Auth required:** Yes, teacher only

### `POST /dashboard/join_class`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Fields:** `code` (string)
- **Success:** Creates Enrollment document, redirects to `/dashboard`
- **Invalid code:** Re-renders student dashboard with `error: "Invalid class code"`
- **Already enrolled:** Silently redirects to `/dashboard`
- **Auth required:** Yes, student only

### `POST /dashboard/manual_enroll`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Fields:** `class_code` (string), `student_emails` (list of strings)
- **Success:** Creates Enrollment documents for each student not already enrolled, redirects to `/dashboard`
- **Auth required:** Yes, teacher only

### `POST /dashboard/reset_assessment`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Fields:** `student_email` (string)
- **Success:** Deletes all Assessment documents for that student, redirects to `/dashboard`
- **Auth required:** Yes, teacher only

### `POST /dashboard/remove_student`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Fields:** `student_email` (string)
- **Success:** Deletes all Enrollment records for that student across the teacher's classes, redirects to `/dashboard`
- **Auth required:** Yes, teacher only

### `POST /dashboard/delete_class`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Fields:** `class_code` (string)
- **Success:** Deletes Class document and all associated Enrollment documents, redirects to `/dashboard`
- **Auth required:** Yes, teacher only

---

## Chat & AI Endpoints

### `GET /dashboard/assistant`
- **Description:** Renders the standalone AI Teaching Assistant page
- **Auth required:** Yes, teacher only

### `POST /dashboard/chat`
- **Content-Type:** `application/json`
- **Body:** `{ "message": string, "conversation_id"?: string, "chat_history"?: list[dict] }`
- **Response:**
  ```json
  {
    "response": "AI response text...",
    "response_truncated": false,
    "conversation": { "id": "...", "title": "...", "is_pinned": false, ... }
  }
  ```
- **Auth required:** Yes, teacher only

### `POST /dashboard/chat_student`
- **Content-Type:** `application/json`
- **Body:** `{ "message": string, "conversation_id"?: string, "chat_history"?: list[dict] }`
- **Response:** Same shape as `/dashboard/chat`
- **Auth required:** Yes, student only
- **Requires:** Assessment on record (or returns 400 error)

### `GET /dashboard/conversations`
- **Query params:** `chat_type` (string: "teacher" or "student")
- **Response:** `{ "conversations": [{ "id", "title", "is_pinned", "updated_at", "created_at", "message_count" }, ...] }`
- **Auth required:** Yes; `chat_type` must match user's role

### `POST /dashboard/conversations`
- **Content-Type:** `application/json`
- **Body:** `{ "chat_type": string, "title"?: string }`
- **Response:** `{ "conversation": { ... } }`
- **Auth required:** Yes

### `GET /dashboard/conversations/{conversation_id}`
- **Query params:** `chat_type` (string)
- **Response:** `{ "conversation": {...}, "messages": [{ "id", "role", "content", "is_truncated", "created_at" }, ...] }`
- **Auth required:** Yes; thread must belong to user

### `PATCH /dashboard/conversations/{conversation_id}`
- **Content-Type:** `application/json`
- **Body:** `{ "chat_type": string, "title"?: string, "is_pinned"?: bool }`
- **Response:** `{ "conversation": {...} }`
- **Auth required:** Yes

### `DELETE /dashboard/conversations/{conversation_id}`
- **Query params:** `chat_type` (string)
- **Response:** `{ "status": "deleted" }`
- **Auth required:** Yes

---

## Document & Email Endpoints

### `POST /dashboard/upload_document`
- **Content-Type:** `multipart/form-data`
- **Fields:** `file` (UploadFile)
- **Response (success):** `{ "filename": "...", "status": "success" }`
- **Response (failure):** `{ "error": "message" }` with 400 or 500 status
- **Auth required:** Yes
- **Supported types:** PDF, DOCX, TXT, PNG, JPG, JPEG, WEBP, BMP, GIF
- **Side effects:** Creates `Material` document; chunks and adds to FAISS index

### `POST /dashboard/send_email`
- **Content-Type:** `application/json`
- **Body:** `{ "recipients": [string, ...], "subject": string, "message": string }`
- **Response (success):** `{ "status": "success", "message": "Dispatched to N students." }`
- **Response (failure):** `{ "error": "..." }` with 500 status
- **Auth required:** Yes, teacher only
- **Backend:** Uses Gmail SMTP with App Password

---

## Root Endpoint

### `GET /`
- **Description:** Root redirect
- **Auth required:** No
- **Behavior:** Redirects to `/auth/login`
