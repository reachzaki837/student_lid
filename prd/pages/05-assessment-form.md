# Learning Assessment

> **Route:** `/assessment/`
> **Module:** Assessment
> **Generated:** 2026-04-10

## Overview

The Learning Assessment page is a single-page, step-by-step questionnaire that determines a student's learning style across two frameworks: **VARK** (4 questions) and **Honey & Mumford** (4 questions). The UI presents one question at a time with animated transitions, a live progress bar, and a selectable card-based option UI. On submission, scores are calculated server-side and stored in MongoDB; the student is redirected to their dashboard where results are displayed.

## Layout

The assessment uses a two-panel layout:

```
┌──────────────┬──────────────────────────────────────────┐
│              │                                          │
│  SIDEBAR     │  QUESTION PANEL                         │
│  (35%)       │  (65%)                                  │
│              │                                          │
│  Logo        │  [QUESTION LABEL]                        │
│  ──────      │  [QUESTION TEXT]                         │
│  Progress    │                                          │
│  [████░░]    │  ┌─────────────┐  ┌─────────────┐       │
│  1 of 8 12%  │  │  Option A   │  │  Option B   │       │
│              │  └─────────────┘  └─────────────┘       │
│  Instructions │  ┌─────────────┐  ┌─────────────┐       │
│  (info card)  │  │  Option C   │  │  Option D   │       │
│              │  └─────────────┘  └─────────────┘       │
│  Est. time   │                                          │
│  remaining   │  ──────────────────────────────────────  │
│  [clock]     │  [← Previous]     [Next Question →]      │
│              │                                          │
└──────────────┴──────────────────────────────────────────┘
```

The sidebar is fixed (white background, full height). The question panel slides in/out with a fade animation on each step change.

## Fields

### Question Types

The assessment contains exactly **8 questions** presented one at a time. Questions 1–4 are VARK questions (4-option multiple choice). Questions 5–8 are Honey & Mumford questions (2-option agree/disagree).

| # | Framework | Field Name | Options | Required |
|---|-----------|------------|---------|----------|
| 1 | VARK | `vark_1` | Visual, Aural, Read/Write, Kinesthetic | Yes |
| 2 | VARK | `vark_2` | Visual, Aural, Read/Write, Kinesthetic | Yes |
| 3 | VARK | `vark_3` | Visual, Aural, Read/Write, Kinesthetic | Yes |
| 4 | VARK | `vark_4` | Visual, Aural, Read/Write, Kinesthetic | Yes |
| 5 | H&M | `hm_1` | Activist, Reflector | Yes |
| 6 | H&M | `hm_2` | Activist, Reflector | Yes |
| 7 | H&M | `hm_3` | Theorist, Pragmatist | Yes |
| 8 | H&M | `hm_4` | Theorist, Pragmatist | Yes |

Each question is represented as a `<input type="radio">` with a corresponding visual card label.

### Navigation State Fields

The form tracks current step client-side (JavaScript) — not as a hidden input field. The final submission always includes all 8 answers regardless of which step the user was on when clicking submit.

## Interactions

### Page Load
- Checks if user is authenticated (redirects to `/auth/login` if not)
- Renders with question step 1 active
- Previous button is hidden (visibility: hidden) on step 1

### Option Card Selection
- **Trigger:** User clicks on an option card
- **Behavior:**
  1. Removes `selected` class from all sibling option cards in the current question
  2. Adds `selected` class to the clicked card
  3. Checks the hidden radio button inside the card
  4. Calls `checkStepValidity()` — enables Next/Submit button (disabled by default until a selection is made)
- Each option card has a visual radio circle indicator that fills with blue when selected

### Next Question Navigation
- **Trigger:** Click "Next Question" button
- **Behavior:** Increments `currentStepIndex`, runs `updateUI()` which hides current step and shows next step with fade animation
- **Button state:** Disabled until an option is selected for the current question

### Previous Question Navigation
- **Trigger:** Click "Previous" button
- **Behavior:** Decrements `currentStepIndex`, runs `updateUI()`
- **Visibility:** Hidden on step 1, visible from step 2 onward

### Step Progress Updates
- **Progress bar:** Width animated from 0% to 100% across all 8 steps (each step = 12.5%)
- **Progress text:** Updates to "Question N of 8"
- **Progress percentage:** Updates to "N*12.5% rounded"
- **Time estimate:** Shows estimated time remaining (mock: 30 seconds per question, displayed as minutes)

### Final Step (Question 8)
- "Next Question" button is replaced by "Submit Assessment" button
- Submit button is disabled until question 8 has an answer selected
- Submit triggers the form POST to `/assessment/submit`

### Form Submission
- **Trigger:** Click "Submit Assessment"
- **API:** POST to `/assessment/submit` as `application/x-www-form-urlencoded`
- **Success:** Server calculates VARK and H&M scores, stores `Assessment` document in MongoDB, redirects to `/dashboard`
- **Server-side scoring logic:**
  - `vark_scores = {"Visual": count of vark_* answers equal to "Visual", ...}`
  - `hm_scores = {"Activist": count of hm_* answers equal to "Activist", ...}`
  - `dominant_style = f"The {max_vark_style} {max_hm_style}"` (e.g., "The Visual Activist")
- **Multiple submissions:** Each submission creates a new `Assessment` document. The dashboard always shows the most recent one (sorted by `created_at` descending).

### Auth Guard
- Unauthenticated users are redirected to `/auth/login`
- No role check — both students and teachers can access this page

## API Dependencies

| API | Method | Path | Trigger | Notes |
|-----|--------|------|---------|-------|
| Assessment Form | GET | `/assessment/` | Navigation | Renders step-by-step form |
| Assessment Submit | POST | `/assessment/submit` | Form submission | Calculates scores, saves Assessment document, redirects to dashboard |

## Page Relationships

- **From:** `/dashboard` (via "Take Assessment" nav link), `/dashboard/student` (via "Start Assessment" CTA when no prior assessment)
- **To:** `/dashboard` (on successful submission)
