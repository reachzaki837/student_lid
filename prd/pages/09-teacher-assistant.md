# AI Teaching Assistant

> **Route:** `/dashboard/assistant`
> **Module:** Teacher
> **Generated:** 2026-04-10

## Overview

The AI Teaching Assistant is a **standalone page version** of the embedded chatbot found on the Teacher Dashboard. It provides the same Perplexity-style research capabilities but renders in a full page instead of a floating panel. Teachers can ask pedagogical questions, get lesson plan suggestions, search the web and YouTube for educational content, and send emails directly to students — all informed by their live classroom data (total students, dominant learning styles, class breakdown).

## Layout

The page renders as a full standalone HTML page (not embedded in the dashboard tab structure). The exact layout of `teacher_assistant.html` was not read, but based on the backend data passed:

```python
{
    "user": user,
    "stats_str": stats_str,       # e.g. "Total Students: 42. Learning Styles Breakdown -> Visual: 12, ..."
    "style_counts": style_counts,
    "class_count": class_count,
    "student_count": student_count,
}
```

The page likely contains:
- Header with logo and user info
- A prominent display of classroom statistics (total students, class count, style distribution)
- A full-page chat interface similar to the embedded chatbot but without size constraints
- Same tools: web search, YouTube search, uploaded course material search, email dispatch

## Fields

### Chat Interface

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Message | Text input | Yes | Teacher's question |
| conversation_id | Hidden | No | For continuing existing threads |

## Interactions

### Page Load
- Authenticates user; redirects to `/auth/login` if unauthenticated
- Verifies `user.role == "teacher"`; redirects to `/auth/login` if student
- Builds teacher stats via `_build_teacher_stats()`:
  - Counts all unique enrolled student emails across all teacher's classes
  - For each student with an assessment, tallies dominant VARK styles
  - Returns formatted `stats_str` for AI context

### Sending a Message
- Same backend handler as the embedded chatbot: `POST /dashboard/chat`
- The AI agent (`AgentService.get_teacher_agent_response()`) receives:
  - The teacher's message
  - `stats_str` with live classroom data
  - Teacher's name and email
  - Chat history (last 6 turns)
- Tools available: `search_uploaded_course_materials`, `search_web`, `search_youtube`, `send_email_to_student`

### AI Response Style
- Formatted with H1/H2 headers, bold text, numbered lists
- Includes "### Recommended Videos" section with YouTube links
- Cites web sources as `[Source](URL)`
- For greetings: responds directly without tool use
- For all other queries: invokes search tools and synthesizes results

## API Dependencies

| API | Method | Path | Trigger | Notes |
|-----|--------|------|---------|-------|
| Assistant Page | GET | `/dashboard/assistant` | Navigation | Full-page render with stats |
| Teacher Chat | POST | `/dashboard/chat` | Message submit | ReAct agent, full page variant |

## Page Relationships

- **From:** Teacher Dashboard sidebar ("AI Assistant" nav link)
- **To:** `/dashboard` (back), `/auth/logout`
