# Login

> **Route:** `/auth/login`
> **Module:** Authentication

## Overview

The login page is the entry point for returning users. It provides two authentication methods: **email/password** via a traditional form, and **Google OAuth 2.0** via a one-click redirect flow. Users who don't yet have an account can navigate to the Register page.

## Layout

The page uses a centered single-card layout on a white background. It is designed for focus and minimal distraction.

```
┌─────────────────────────────────────┐
│  [Logo] StudentLID                  │
│                                     │
│  Welcome back                       │
│  Please enter your details...       │
│                                     │
│  [  Continue with Google  ]         │
│                                     │
│  ─────────── or ───────────          │
│                                     │
│  Email Address                      │
│  [___________________________]       │
│                                     │
│  Password                           │
│  [___________________________]       │
│                                     │
│  [Remember me]    [Forgot password?]│
│                                     │
│  [        Sign In →        ]        │
│                                     │
│  Don't have an account? Register...  │
└─────────────────────────────────────┘
```

## Fields

### Form Fields

| Field | Type | Required | Default | Validation | Business Description |
|-------|------|----------|---------|------------|---------------------|
| Email Address | Text input (email) | Yes | — | Must be valid email format | User's registered email address |
| Password | Password input | Yes | — | — | Account password (obscured) |

### Interactive Elements

| Element | Behavior |
|---------|----------|
| "Continue with Google" button | Navigates to `/auth/google` endpoint, which redirects to Google's OAuth consent screen |
| "Forgot password?" link | Navigates to `/auth/forgot-password` |
| "Register a new account" link | Navigates to `/auth/register` |

## Interactions

### Page Load
- Page renders with empty form fields
- Error message displayed if redirected from another page with an `?error=` query parameter (e.g., from Google OAuth failure or session expiry)
- Success/info message displayed if redirected with a `?message=` query parameter (e.g., "Password updated. Please sign in." after a successful password reset)

### Email/Password Login
- **Trigger:** User fills email and password fields and clicks "Sign In"
- **Validation:** Both fields are HTML `required`; backend additionally checks that the user exists and password matches
- **API:** POST to `/auth/login` with `application/x-www-form-urlencoded` form data
- **Success:** Server creates JWT cookie, redirects to `/dashboard`
- **Failure:** Page re-renders with error message "Invalid email or password"

### Google OAuth Login
- **Trigger:** User clicks "Continue with Google" button
- **Behavior:** Browser navigates to `/auth/google`, which immediately issues a 302 redirect to `https://accounts.google.com/o/oauth2/v2/auth` with OAuth parameters including `client_id`, `redirect_uri`, `scope=openid email profile`, `access_type=offline`, and `prompt=select_account`
- **Callback:** After user grants permission, Google redirects to `/auth/google/callback?code=XXX`
- **Callback behavior (existing user):** Server exchanges code for tokens, fetches user info, finds existing user by email, creates JWT, redirects to `/dashboard`
- **Callback behavior (new user):** Server redirects to `/auth/register?google_name=...&google_email=...&google_id=...&google_picture=...` with Google user data pre-filled for registration
- **Callback failure:** Redirects to `/auth/login?error=Google+sign-in+was+cancelled` or similar descriptive error

### Error Display
- **Trigger:** Error query parameter present on page load
- **Display:** Red alert box at top of card: `<div class="error-alert"><i class="bi bi-exclamation-circle me-1"></i> {{ error }}</div>`
- **Known error messages:**
  - `Google+sign-in+was+cancelled` — User cancelled Google OAuth
  - `Failed+to+connect+with+Google` — Token exchange failed
  - `Failed+to+get+user+info+from+Google` — User info fetch failed
  - `Google+authentication+service+unavailable` — HTTP error during OAuth
  - `Google+did+not+provide+an+email` — Google's user info missing email

## API Dependencies

| API | Method | Path | Trigger | Notes |
|-----|--------|------|---------|-------|
| Login | POST | `/auth/login` | Form submission | Creates JWT HttpOnly cookie, redirects on success |
| Google Auth Init | GET | `/auth/google` | Button click | Server-side redirect to Google's OAuth endpoint |
| Google Callback | GET | `/auth/google/callback` | OAuth redirect | Handles code exchange, user lookup, JWT creation |

## Page Relationships

- **From:** Root `/` → redirects here; Google OAuth failure → redirects here with error; successful password reset → redirects here with `?message=`
- **To:** `/auth/register` (register link), `/dashboard` (success), `/auth/google` (Google button), `/auth/forgot-password` (forgot password link)
