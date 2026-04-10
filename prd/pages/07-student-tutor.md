# AI Study Tutor

> **Route:** `/dashboard/tutor`
> **Module:** Student
> **Generated:** 2026-04-10

## Overview

The AI Study Tutor page provides each student with a personalized AI-powered chatbot that adapts its explanations to their specific learning style combination (VARK dominant + Honey & Mumford dominant). The tutor uses a LangChain ReAct agent that can search the web, YouTube, and uploaded course materials to provide rich, research-grounded answers. The page renders a persistent chat interface where conversations are saved and can be continued across sessions.

## Layout

The exact layout of `student_chat.html` was not read, but based on the backend route `/dashboard/tutor` (GET) and `/dashboard/chat_student` (POST), the page:

- Requires student authentication (redirects to `/auth/login` if not authenticated or not a student)
- Requires a completed assessment (redirects to `/assessment` if no assessment found)
- Displays the student's learning style prominently
- Contains a chat interface with message history, an input field, and send button
- Persists conversation via `conversation_id` tracked across requests

## Fields

### Chat Input

| Field | Type | Required | Max Length | Notes |
|-------|------|----------|-----------|-------|
| Message | Text input | Yes | 4000 chars | Student's question or message |
| conversation_id | Hidden or query param | No | — | ID of the ConversationThread to continue; if omitted, a new thread is created |

## Interactions

### Page Load
- Authenticates user; redirects to `/auth/login` if unauthenticated
- Checks `user.role == "student"`; redirects to `/auth/login` if teacher
- Loads the most recent `Assessment` for the user to determine VARK and H&M styles
- If no assessment found, redirects to `/assessment` to force completion first
- Renders the chat interface template

### Sending a Message
- **Trigger:** User types a message and submits (Enter key or send button)
- **API:** POST JSON to `/dashboard/chat_student`
  ```json
  { "message": "...", "conversation_id": "optional_thread_id", "chat_history": [...] }
  ```
- **Server behavior:**
  1. Validates message is non-empty
  2. Resolves or creates a `ConversationThread` for this user
  3. Loads existing chat history from the thread if no `chat_history` provided
  4. Extracts VARK and H&M dominant styles from the user's most recent assessment
  5. Calls `AgentService.get_student_tutor_response(message, vark_style, hm_style, chat_history)`
  6. Appends the user message and AI response to the conversation thread
  7. Auto-generates thread title from first message if this is the first turn
  8. Truncates messages exceeding per-turn limits (user: 4000 chars, assistant: 12000 chars)
  9. Enforces max 100 messages per thread, evicting oldest when exceeded
- **Response:**
  ```json
  {
    "response": "AI tutor's answer...",
    "response_truncated": false,
    "conversation": { "id": "...", "title": "...", "is_pinned": false, ... }
  }
  ```

### AI Agent Behavior
- The agent uses a **ReAct loop** with tools: `search_web`, `search_youtube`, `search_uploaded_course_materials`
- For simple non-research questions (no keywords like "latest", "news", "search", "video", etc.), a **fast path** bypasses tool use and directly calls the LLM
- For research questions, the agent invokes all tools and synthesizes a Perplexity-style response with citations and video recommendations
- Provider chain: Google Gemini → Groq LLaMA fallback with retry logic
- Error responses are user-friendly messages (not raw error strings)

### Conversation Persistence
- `ConversationThread` documents store messages as an array of `ConversationMessage` embedded objects
- Threads are scoped to a specific `(owner_email, owner_role)` combination — students cannot see teacher threads
- Thread titles auto-generated from first message (up to 60 characters, truncated with "...")
- Threads support pinning (future use; toggle exists in the backend)

## API Dependencies

| API | Method | Path | Trigger | Notes |
|-----|--------|------|---------|-------|
| Tutor Page | GET | `/dashboard/tutor` | Navigation | Renders chat UI; requires auth + assessment |
| Student Chat | POST | `/dashboard/chat_student` | Message submit | ReAct agent, returns AI response |
| List Conversations | GET | `/dashboard/conversations?chat_type=student` | Chat UI (likely) | Returns list of student's threads |
| Get Conversation | GET | `/dashboard/conversations/{id}?chat_type=student` | Chat UI | Returns thread with all messages |

## Page Relationships

- **From:** `/dashboard` (via "AI Study Tutor" sidebar link)
- **To:** `/dashboard` (back), `/auth/logout` (logout)
