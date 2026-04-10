# Register

> **Route:** `/auth/register`
> **Module:** Authentication
> **Generated:** 2026-04-10

## Overview

The registration page accepts new users and supports two flows: (1) standard email/password registration, and (2) Google OAuth completion registration (pre-filled with Google user data when arriving from the OAuth callback). New users choose their role — **Student** (default) or **Teacher** — which determines their dashboard experience.

## Layout

Uses the same centered card visual language as the login page for design consistency.

```
┌─────────────────────────────────────┐
│  [Logo] StudentLID                  │
│                                     │
│  Create your account                │
│  Join or start a learning community │
│                                     │
│  Name                               │
│  [___________________________]        │
│                                     │
│  Email Address                      │
│  [___________________________]        │
│                                     │
│  Password (for manual registration) │
│  [___________________________]        │
│                                     │
│  I am a:  ○ Student  ● Teacher      │
│                                     │
│  [     Create Account →      ]       │
│                                     │
│  Already have an account? Sign in   │
└─────────────────────────────────────┘
```

When arriving from Google OAuth, the form is pre-filled with Google-provided data and the Google profile picture is shown. The name and email fields may be read-only or pre-filled.

## Fields

### Form Fields

| Field | Type | Required | Default | Validation | Business Description |
|-------|------|----------|---------|------------|---------------------|
| Full Name | Text input | Yes | — | Must be non-empty after trim | Display name shown on dashboard |
| Email Address | Text input (email) | Yes | — | Must be valid email format; must not already exist | Unique account identifier |
| Password | Password input | Conditionally | — | Minimum 6 characters | Required for local auth; not required for Google sign-up |
| Role | Radio button group | Yes | `student` | Must be `student` or `teacher` | Determines which dashboard the user sees after login |

### Hidden Fields (Google OAuth flow)

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| google_id | Hidden input | Google OAuth callback | Unique Google user ID for account linking |
| google_picture | Hidden input | Google OAuth callback | URL of user's Google profile picture |

## Interactions

### Standard Registration
- **Trigger:** User fills name, email, password (and optionally role), then clicks "Create Account"
- **Validation:**
  - Name cannot be empty after whitespace trim
  - Password required for local registration (error: "Password is required")
  - Email must not already exist in the database (error: "Email already registered")
- **API:** POST to `/auth/register` as `application/x-www-form-urlencoded`
- **Success:** Redirects to `/auth/login` for the user to log in with new credentials
- **Failure:** Re-renders page with error message

### Google OAuth Registration
- **Trigger:** User arrives at `/auth/register?google_name=...&google_email=...&google_id=...&google_picture=...` from Google OAuth callback
- **Behavior:** Name, email fields pre-filled; `google_id` and `google_picture` stored as hidden fields; password field hidden or marked optional
- **Submission:** User fills name (if not pre-filled), selects role, clicks "Create Account"; POST includes all google_* fields
- **Backend logic:** Detects `google_id` presence and calls `AuthService.create_google_user()` instead of `create_user()`
- **Success:** Directly creates JWT and redirects to `/dashboard` (skips login step since Google identity is confirmed)
- **Failure:** "Email already registered" error if a local account with that email already exists

### Role Selection
- Two radio buttons: "Student" (default, visually first) and "Teacher"
- Changing role does not alter form fields, only the account type stored in MongoDB
- Role determines which dashboard template is shown: `student.html` vs. `teacher.html`

## API Dependencies

| API | Method | Path | Trigger | Notes |
|-----|--------|------|---------|-------|
| Register | POST | `/auth/register` | Form submission | Creates user in MongoDB; creates JWT cookie on Google flow |
| Google Callback | GET | `/auth/google/callback` | OAuth redirect | Detects new vs. existing user, redirects accordingly |

## Page Relationships

- **From:** `/auth/login` (register link), `/auth/google/callback` (new Google users)
- **To:** `/auth/login` (success of local registration), `/dashboard` (success of Google registration)
