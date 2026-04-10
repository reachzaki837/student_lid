# Forgot Password

> **Route:** `/auth/forgot-password`
> **Module:** Authentication
> **Generated:** 2026-04-10

## Overview

The Forgot Password page allows users who have forgotten their password to request a secure, time-limited password reset link delivered to their registered email address. The page accepts only an email address, validates it server-side, and — if a local (non-Google) account exists — sends a branded HTML email containing a single-use reset link. The page intentionally shows the same success message for both known and unknown emails to prevent account enumeration attacks.

## Layout

The page uses the same centered single-card layout as the Login page for visual consistency.

```
┌─────────────────────────────────────┐
│  [Logo] StudentLID                  │
│                                     │
│  Forgot password?                   │
│  Enter your email and we will send │
│  you a one-time reset link.        │
│                                     │
│  Email Address                      │
│  [___________________________]       │
│                                     │
│  [     Send reset link →     ]     │
│                                     │
│  Remembered your password?           │
│  Back to login                      │
└─────────────────────────────────────┘
```

When the form is successfully submitted, the page re-renders with an informational success message: *"If an account exists for that email, a password reset link has been sent."*

## Fields

### Form Fields

| Field | Type | Required | Default | Validation | Business Description |
|-------|------|----------|---------|------------|---------------------|
| Email Address | Text input (email) | Yes | — | Must be valid email format | Registered email address for the account to reset |

## Interactions

### Page Load
- Renders the form with an empty email field
- Displays a `message` query parameter as an info alert (blue) if redirected back after submission
- No authentication check — this page is public

### Submit Reset Request
- **Trigger:** User enters an email address and clicks "Send reset link"
- **API:** POST to `/auth/forgot-password` as `application/x-www-form-urlencoded`
- **Server behavior:**
  1. Looks up the email in the User collection
  2. If no user found → silently returns success (no enumeration)
  3. If user found but is Google OAuth only (no local password) → silently returns success
  4. If local user found:
     - Generates a cryptographically random token via `secrets.token_urlsafe(32)`
     - Stores the HMAC-SHA256 hash of the token in `User.password_reset_token_hash`
     - Sets `User.password_reset_expires_at` to 60 minutes from now
     - Saves the user document
     - Sends a branded HTML email via Gmail SMTP containing the reset link
- **Success:** Page re-renders with info message "If an account exists for that email, a password reset link has been sent."
- **Email delivery failure:** The page still shows success (email sending failure is logged server-side but not surfaced to the user)

### Back to Login
- **Trigger:** User clicks "Back to login" link
- **Behavior:** Navigates to `/auth/login`

## Security Design

### Account Enumeration Prevention
The system returns the identical success message whether the email is registered or not. An attacker cannot distinguish between "email not found" and "email found but Google account."

### Token Security
- **Storage:** Only the HMAC-SHA256 hash of the token is stored in MongoDB, never the plaintext token
- **Hashing:** Uses `settings.SECRET_KEY` as the HMAC key
- **Expiry:** Tokens expire after 60 minutes (`PASSWORD_RESET_TTL_MINUTES`)
- **Single-use:** After successful password change, both `password_reset_token_hash` and `password_reset_expires_at` are cleared

## API Dependencies

| API | Method | Path | Trigger | Notes |
|-----|--------|------|---------|-------|
| Forgot Password Page | GET | `/auth/forgot-password` | Navigation | Public; accepts `?message=` query param |
| Forgot Password Submit | POST | `/auth/forgot-password` | Form submission | Sends email if local account exists |

## Page Relationships

- **From:** `/auth/login` (via "Forgot password?" link)
- **To:** `/auth/login` (back to login link), `/auth/reset-password` (via email link)
