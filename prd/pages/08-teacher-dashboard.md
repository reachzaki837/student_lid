# Teacher Dashboard

> **Route:** `/dashboard` (when `user.role == "teacher"`)
> **Module:** Teacher
> **Generated:** 2026-04-10

## Overview

The Teacher Dashboard is the primary interface for instructors. It surfaces real-time classroom intelligence: enrolled student counts, class-level learning style distributions aggregated across all classes, a per-student breakdown showing each student's dominant VARK/H&M style, and action menus for managing individual students (reset assessment, remove from classes). Teachers can also create new classes, manage existing ones, and trigger email communications to students. The dashboard also embeds a **draggable and resizable AI chatbot** (floating panel, bottom-right) that provides Perplexity-style research assistance informed by the teacher's live classroom data.

The dashboard uses a **tabbed interface** with two main tabs: "Dashboard" (default) and "My Classes".

## Layout

```
┌──────────────┬──────────────────────────────────────────────────────────────┐
│  SIDEBAR    │  MAIN CONTENT                                                 │
│  (260px)    │                                                                │
│              │  Teacher Dashboard                        [Open AI] [Export ▾] │
│  Logo        │  Welcome back, Professor. Here's what's happening today.      │
│  ──────      │                                                                │
│  Dashboard   │  ┌─────────────────┐  ┌─────────────────┐                  │
│  My Classes  │  │ Total Students  │  │ Active Classes  │                  │
│  AI Assistant│  │      42         │  │       3         │                  │
│  Settings    │  └─────────────────┘  └─────────────────┘                  │
│              │                                                                │
│  ──────      │  ┌───────────────────────────────────────────────────────┐   │
│  User Avatar │  │ Learning Styles Distribution  [Bar Chart]              │   │
│  Name        │  └───────────────────────────────────────────────────────┘   │
│  Logout      │                                                                │
│              │  ┌───────────────────────────────────────────────────────┐   │
│              │  │ Students                              [Compose Email] │   │
│              │  │ Name | Email | Dept | Style | Actions               │   │
│              │  │ ─────────────────────────────────────────────────── │   │
│              │  │ John  | ...  | CS  | [Visual] | ⋮                  │   │
│              │  └───────────────────────────────────────────────────────┘   │
│              │                                                        [💬] │
└──────────────┴──────────────────────────────────────────────────────────────┘

             ┌─────────────────────────────────┐
             │ 💬 Class Insights Assistant   [X]│
             │─────────────────────────────────│
             │ Hi! You have 42 active students │
             │ [typing input here...]    [📎][➤]│
             └─────────────────────────────────┘
```

The chatbot panel is draggable (by header) and resizable (by corner handles). It defaults to bottom-right.

## Fields

### Dashboard Tab

No direct form fields on the main dashboard tab. Data is loaded server-side from MongoDB.

### Classes Tab

#### Create Class Form

| Field | Type | Required | Default | Validation | Notes |
|-------|------|----------|---------|------------|-------|
| Class Name | Text input | Yes | — | — | e.g., "Bio 101", "CS Fundamentals" |

#### Enroll Students Modal

| Field | Type | Required | Default | Validation | Notes |
|-------|------|----------|---------|------------|-------|
| Class Code | Select dropdown | Yes | First class in list | — | Populated from teacher's existing classes |
| Student Emails | Multi-checkbox list | At least 1 | — | Must be registered student accounts | All students in the system shown; already-enrolled ones pre-checked and disabled |

### Student Table Columns

| Column | Format | Sortable | Filterable | Notes |
|--------|--------|----------|-----------|-------|
| Student Name | Text | No | No | From User.name |
| Email | Text | No | No | Student email address |
| Department | Text | No | No | Auto-parsed from email |
| Degree | Text | No | No | Auto-parsed from email |
| Academic Progress | Text | No | No | e.g., "2021-2025 \| III Year \| Sem 5" |
| Status / Badge | Colored badge | No | No | Visual/Aural/Read/Write/Kinesthetic/Pending |
| Actions | Dropdown menu | No | No | View Profile, Reset Assessment, Remove Student |

### Actions Dropdown

| Action | Behavior |
|--------|----------|
| View Profile | Opens a Bootstrap modal showing student name, email, dominant style badge, and VARK/H&M score breakdowns |
| Reset Assessment | POST to `/dashboard/reset_assessment` with `student_email`; deletes all Assessment documents for that student |
| Remove Student | POST to `/dashboard/remove_student` with `student_email`; deletes all Enrollment records for that student across all the teacher's classes |

### Email Composer Modal

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| Recipients | Radio: Entire Class / Specific Students | Yes | Entire Class | Toggles student checklist |
| Student Checklist | Multi-checkbox list | Conditional | All students | Searchable; only shown when "Specific Students" is selected |
| Subject | Text input | Yes | — | Max 200 chars recommended |
| Message Body | Textarea (5 rows) | Yes | — | Email body text |

### Export Dropdown

Four export formats: **PDF**, **CSV**, **Excel**, **JSON**. Each triggers client-side generation using JS libraries (jsPDF, native Blob). Exports include student name, email, dominant style, and all four VARK sub-scores.

### Embedded Chatbot

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Chat Input | Text input | Yes | Single-line input; submits on Enter key |
| Attachment Button | Button | No | Opens upload modal for course materials |

## Interactions

### Tab Navigation
- **Trigger:** Click sidebar nav link ("Dashboard" or "My Classes")
- **Behavior:** JavaScript `switchTab()` hides all `.tab-content` divs, shows the matching `#tab-{id}`, updates active state on sidebar links
- **URL does not change** (no client-side routing; full page reloads on sidebar nav)

### Dashboard Tab Load
- Authenticates user; redirects to `/auth/login` if unauthenticated or not a teacher
- Loads all classes owned by this teacher
- Loads all enrollments across those classes → derives unique enrolled student emails
- For each unique student email: fetches the User document, most recent Assessment, email profile
- Builds `student_data` list with style counts for the bar chart
- Renders bar chart using Chart.js with 4 bars (Visual, Aural, Read/Write, Kinesthetic)

### Create Class
- **Trigger:** Fill class name and click "+ Create Class"
- **API:** POST form to `/dashboard/create_class`
- **Behavior:** Generates a random 6-character alphanumeric code, creates a `Class` document, redirects to `/dashboard`
- **Multiple submissions:** Each submission creates a new class with a unique code

### Join Class (Student-side, not teacher)
- N/A on teacher dashboard

### Delete Class
- **Trigger:** Click "Delete" button on a class row (with confirmation dialog)
- **API:** POST to `/dashboard/delete_class` with `class_code`
- **Behavior:** Deletes the Class document and all associated Enrollment documents
- **Does not delete:** Assessment documents or User documents (students remain registered)

### Manual Enroll Students
- **Trigger:** Select a class from dropdown, check students, click "Enroll Selected"
- **API:** POST to `/dashboard/manual_enroll` with `class_code` + multiple `student_emails` values
- **Validation:** Teacher must own the class; skips already-enrolled students silently
- **Feedback:** Page reloads with updated enrollment state

### View Student Profile Modal
- **Trigger:** Click "View Profile" in the student action dropdown
- **Behavior:** Opens modal with student name, email, style badge, VARK score breakdown, H&M score breakdown
- **Data source:** Pre-rendered into `data-*` attributes on each "View Profile" button (no API call)

### Reset Student Assessment
- **Trigger:** Click "Reset Assessment" in the student action dropdown
- **API:** POST to `/dashboard/reset_assessment` with `student_email`
- **Behavior:** Deletes all Assessment documents for that student from MongoDB
- **Note:** This does not auto-redirect the student to re-take the assessment; they simply show as "Pending" on next dashboard load

### Remove Student
- **Trigger:** Click "Remove Student" (with browser confirmation dialog)
- **API:** POST to `/dashboard/remove_student` with `student_email`
- **Behavior:** Deletes all Enrollment records for this student across all classes owned by this teacher
- **Does not delete:** User account, Assessment records

### Email Compose and Send
- **Trigger:** Click "Compose Email" → fill modal form → click "Send"
- **API:** POST JSON to `/dashboard/send_email`
  ```json
  { "recipients": ["email1", "email2"], "subject": "...", "message": "..." }
  ```
- **Behavior:** Teacher sends to entire class (all enrolled students) or specific selected students
- **Backend:** `send_class_email()` uses Gmail SMTP with App Password; runs in a thread

### Document Upload
- **Trigger:** Click attachment icon in chatbot footer → select file in modal → click "Upload to AI Brain"
- **API:** POST multipart/form-data to `/dashboard/upload_document`
- **Supported types:** PDF, DOCX, TXT, PNG, JPG, JPEG, WEBP, BMP, GIF
- **Behavior:** Extracts text (PDF via PyPDF2, DOCX via python-docx, images via Gemini vision), saves `Material` document, chunks text, and adds to FAISS vector store
- **Max size:** No explicit limit; constrained by server resources

### Chatbot Toggle
- **Trigger:** Click floating chat button (bottom-right)
- **Behavior:** Toggles `.chat-window` visibility (adds/removes `open` class)

### Chat Message Send
- **Trigger:** Type message + press Enter or click send button
- **API:** POST JSON to `/dashboard/chat`
  ```json
  { "message": "...", "conversation_id": "optional" }
  ```
- **Response:** AI response rendered as HTML (via `marked.parse()`), chat history displayed in scrollable panel
- **Agent:** `AgentService.get_teacher_agent_response()` — uses tools: `search_uploaded_course_materials`, `search_web`, `search_youtube`, `send_email_to_student`

## API Dependencies

| API | Method | Path | Trigger | Notes |
|-----|--------|------|---------|-------|
| Dashboard Load | GET | `/dashboard` | Navigation | Renders teacher template based on role |
| Create Class | POST | `/dashboard/create_class` | Create class form | Generates 6-char code, creates Class doc |
| Join Class | POST | `/dashboard/join_class` | N/A (teacher) | Not used by teacher |
| Manual Enroll | POST | `/dashboard/manual_enroll` | Enroll modal | Bulk enroll by email |
| Reset Assessment | POST | `/dashboard/reset_assessment` | Student action | Deletes Assessment docs |
| Remove Student | POST | `/dashboard/remove_student` | Student action | Deletes Enrollment docs |
| Delete Class | POST | `/dashboard/delete_class` | Class action | Cascades to Enrollments |
| Send Email | POST | `/dashboard/send_email` | Email modal | Gmail SMTP dispatch |
| Upload Document | POST | `/dashboard/upload_document` | Upload modal | FAISS indexing + Material doc |
| Teacher Chat | POST | `/dashboard/chat` | Chat input | ReAct agent with class stats |
| List Conversations | GET | `/dashboard/conversations?chat_type=teacher` | Chat UI | Teacher's threads |

## Page Relationships

- **From:** Login (role determines teacher template), Register (teacher role)
- **To:** `/dashboard/assistant` (AI Assistant page), `/dashboard/settings`, `/auth/logout`
